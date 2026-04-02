import os
import uuid
import redis


class MultiRedisLock:
    def __init__(self, keys, ttl_seconds):
        self.keys = list(keys)
        self.ttl_seconds = int(ttl_seconds)
        self.token = str(uuid.uuid4())
        self._acquired = []
        self._client = None

    def __enter__(self):
        url = os.environ.get("REDIS_LOCK_URL") or os.environ.get("CELERY_BROKER_URL") or "redis://127.0.0.1:6379/0"
        self._client = redis.Redis.from_url(url, decode_responses=True)
        for k in self.keys:
            ok = self._client.set(k, self.token, nx=True, ex=self.ttl_seconds)
            if not ok:
                self.release()
                return None
            self._acquired.append(k)
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False

    def release(self):
        if not self._client or not self._acquired:
            return
        script = """
if redis.call("get", KEYS[1]) == ARGV[1] then
  return redis.call("del", KEYS[1])
else
  return 0
end
"""
        for k in self._acquired:
            self._client.eval(script, 1, k, self.token)
        self._acquired = []


def seat_lock_keys(event_id, seat_ids):
    ids = sorted(int(s) for s in seat_ids)
    return [f"lock:event:{int(event_id)}:seat:{sid}" for sid in ids]

