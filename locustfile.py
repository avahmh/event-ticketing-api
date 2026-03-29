import uuid
from locust import HttpUser, task, between


class TicketingUser(HttpUser):
    wait_time = between(0.5, 2.0)

    @task(5)
    def list_events(self):
        self.client.get("/events/")

    @task(3)
    def purchase_ticket(self):
        event_id = 1
        self.client.post(
            f"/events/{event_id}/tickets/",
            data={"quantity": 1},
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )

    @task(1)
    def list_orders(self):
        self.client.get("/events/1/orders/")

    @task(1)
    def get_seatmap(self):
        self.client.get("/events/1/seatmap/")
