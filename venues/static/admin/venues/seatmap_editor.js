(function () {
  function initSeatmapEditor() {
  const root = document.getElementById("seatmap-editor-root");
  const ta = document.getElementById("id_layout_json");
  if (!root || !ta) return false;
  if (root.getAttribute("data-seatmap-mounted") === "1") return true;
  root.setAttribute("data-seatmap-mounted", "1");

  const PAD = 48;
  const CELL = 20;
  const KINDS = [
    ["standard", "عادی"],
    ["vip", "VIP"],
    ["wheelchair", "ویلچر"],
    ["blocked", "مسدود"],
  ];

  function defaultLayout() {
    return {
      version: 2,
      grid: { cols: 32, rows: 20 },
      stage: { edge: "north", label: "صحنه اجرا" },
      cells: [],
    };
  }

  function readLayout() {
    try {
      const v = JSON.parse(ta.value.trim() || "{}");
      if (v.version !== 2) return defaultLayout();
      if (!v.grid) v.grid = { cols: 32, rows: 20 };
      if (!v.grid.cols) v.grid.cols = 32;
      if (!v.grid.rows) v.grid.rows = 20;
      if (!Array.isArray(v.cells)) v.cells = [];
      if (!v.stage) v.stage = { edge: "north", label: "صحنه" };
      return v;
    } catch (e) {
      return defaultLayout();
    }
  }

  function writeLayout(L) {
    ta.value = JSON.stringify(L, null, 2);
    ta.dispatchEvent(new Event("input", { bubbles: true }));
    ta.dispatchEvent(new Event("change", { bubbles: true }));
  }

  const boot = document.getElementById("hall-layout-bootstrap");
  if (boot) {
    try {
      const b = JSON.parse(boot.textContent.trim());
      if (b && b.version === 2 && (!ta.value.trim() || JSON.parse(ta.value).version !== 2)) {
        writeLayout(b);
      }
    } catch (e) {}
  }
  if (!ta.value.trim()) {
    writeLayout(defaultLayout());
  }

  function cellMap(L) {
    const m = new Map();
    for (const c of L.cells) {
      m.set(c.c + "," + c.r, c);
    }
    return m;
  }

  function getCell(L, c, r) {
    return cellMap(L).get(c + "," + r);
  }

  function setCell(L, c, r, cell) {
    const key = c + "," + r;
    L.cells = L.cells.filter(function (x) {
      return x.c + "," + x.r !== key;
    });
    if (cell && cell.t !== "e") {
      L.cells.push(
        Object.assign({ c: c, r: r }, cell)
      );
    }
    writeLayout(L);
  }

  function bresenham(c0, r0, c1, r1) {
    const out = [];
    let c = c0;
    let r = r0;
    const dc = Math.abs(c1 - c0);
    const dr = Math.abs(r1 - r0);
    const sc = c0 < c1 ? 1 : c0 > c1 ? -1 : 0;
    const sr = r0 < r1 ? 1 : r0 > r1 ? -1 : 0;
    let err = dc - dr;
    while (true) {
      out.push([c, r]);
      if (c === c1 && r === r1) break;
      const e2 = 2 * err;
      if (e2 > -dr) {
        err -= dr;
        c += sc;
      }
      if (e2 < dc) {
        err += dc;
        r += sr;
      }
    }
    return out;
  }

  let tool = "brush";
  let brushT = "s";
  let seatKind = "standard";
  let scale = 1;
  let offsetX = 20;
  let offsetY = 20;
  let spaceDown = false;
  let selection = new Set();
  let isDown = false;
  let mode = null;
  let lastCR = null;
  let selRect = null;
  let moveFrom = null;
  let panFrom = null;
  let lastPaint = null;
  let lastMx = 0;
  let lastMy = 0;

  const toolbar = document.createElement("div");
  toolbar.className = "seatmap-editor-toolbar";

  function mkBtn(label, t) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    b.addEventListener("click", function () {
      tool = t;
      Array.from(toolbar.querySelectorAll("button[data-tool]")).forEach(function (x) {
        x.classList.toggle("tool-active", x.getAttribute("data-tool") === t);
      });
    });
    b.setAttribute("data-tool", t);
    return b;
  }

  toolbar.appendChild(mkBtn("قلم‌مو", "brush"));
  toolbar.appendChild(mkBtn("پاک‌کن", "erase"));
  toolbar.appendChild(mkBtn("انتخاب", "select"));
  toolbar.appendChild(mkBtn("جابه‌جا", "move"));
  toolbar.appendChild(mkBtn("پَن", "pan"));

  const brushSel = document.createElement("select");
  [
    ["e", "خالی"],
    ["a", "راهرو"],
    ["st", "صحنه"],
    ["s", "صندلی"],
  ].forEach(function (o) {
    const op = document.createElement("option");
    op.value = o[0];
    op.textContent = o[1];
    brushSel.appendChild(op);
  });
  brushSel.value = "s";
  brushSel.addEventListener("change", function () {
    brushT = brushSel.value;
  });
  toolbar.appendChild(document.createTextNode(" سلول: "));
  toolbar.appendChild(brushSel);

  const kindSel = document.createElement("select");
  KINDS.forEach(function (kv) {
    const op = document.createElement("option");
    op.value = kv[0];
    op.textContent = kv[1];
    kindSel.appendChild(op);
  });
  kindSel.addEventListener("change", function () {
    seatKind = kindSel.value;
  });
  toolbar.appendChild(document.createTextNode(" نوع صندلی: "));
  toolbar.appendChild(kindSel);

  const colsIn = document.createElement("input");
  colsIn.type = "number";
  colsIn.min = "8";
  colsIn.max = "120";
  colsIn.style.width = "3.5rem";
  const rowsIn = document.createElement("input");
  rowsIn.type = "number";
  rowsIn.min = "8";
  rowsIn.max = "120";
  rowsIn.style.width = "3.5rem";

  const applyGrid = document.createElement("button");
  applyGrid.type = "button";
  applyGrid.textContent = "اعمال شبکه";
  applyGrid.addEventListener("click", function () {
    const L = readLayout();
    const nc = Math.max(8, Math.min(120, parseInt(colsIn.value, 10) || 32));
    const nr = Math.max(8, Math.min(120, parseInt(rowsIn.value, 10) || 20));
    L.grid.cols = nc;
    L.grid.rows = nr;
    L.cells = L.cells.filter(function (x) {
      return x.c < nc && x.r < nr;
    });
    writeLayout(L);
    draw();
  });
  toolbar.appendChild(document.createTextNode(" ستون "));
  toolbar.appendChild(colsIn);
  toolbar.appendChild(document.createTextNode(" ردیف "));
  toolbar.appendChild(rowsIn);
  toolbar.appendChild(applyGrid);

  const zoomIn = document.createElement("button");
  zoomIn.type = "button";
  zoomIn.textContent = "+";
  zoomIn.addEventListener("click", function () {
    scale = Math.min(3, scale * 1.15);
    draw();
  });
  const zoomOut = document.createElement("button");
  zoomOut.type = "button";
  zoomOut.textContent = "−";
  zoomOut.addEventListener("click", function () {
    scale = Math.max(0.35, scale / 1.15);
    draw();
  });
  const zoomReset = document.createElement("button");
  zoomReset.type = "button";
  zoomReset.textContent = "زوم ۱×";
  zoomReset.addEventListener("click", function () {
    scale = 1;
    offsetX = 20;
    offsetY = 20;
    draw();
  });
  toolbar.appendChild(zoomIn);
  toolbar.appendChild(zoomOut);
  toolbar.appendChild(zoomReset);
  toolbar.querySelector('button[data-tool="brush"]').classList.add("tool-active");

  const labelBtn = document.createElement("button");
  labelBtn.type = "button";
  labelBtn.textContent = "برچسب صندلی‌ها";
  labelBtn.addEventListener("click", function () {
    const L = readLayout();
    const keys = Array.from(selection);
    if (!keys.length) return;
    const cells = keys
      .map(function (k) {
        const p = k.split(",");
        return { c: parseInt(p[0], 10), r: parseInt(p[1], 10) };
      })
      .filter(function (x) {
        const cell = getCell(L, x.c, x.r);
        return cell && cell.t === "s";
      })
      .sort(function (a, b) {
        return a.r - b.r || a.c - b.c;
      });
    if (!cells.length) return;
    const byR = {};
    cells.forEach(function (x) {
      if (!byR[x.r]) byR[x.r] = [];
      byR[x.r].push(x);
    });
    const rs = Object.keys(byR)
      .map(function (x) {
        return parseInt(x, 10);
      })
      .sort(function (a, b) {
        return a - b;
      });
    let letter = 65;
    rs.forEach(function (r) {
      const rowCells = byR[r].sort(function (a, b) {
        return a.c - b.c;
      });
      const lab = String.fromCharCode(letter);
      letter += 1;
      if (letter > 90) letter = 65;
      rowCells.forEach(function (x, i) {
        const cell = getCell(L, x.c, x.r);
        if (!cell) return;
        cell.row_label = lab;
        cell.seat_number = String(i + 1);
        setCell(L, x.c, x.r, cell);
      });
    });
    draw();
  });
  toolbar.appendChild(labelBtn);

  root.appendChild(toolbar);

  const hint = document.createElement("div");
  hint.className = "seatmap-hint";
  hint.textContent =
    "اسپیس + درگ = پَن. حذف = پاک کردن انتخاب. اسکرول = زوم روی نشانگر.";
  root.appendChild(hint);

  const wrap = document.createElement("div");
  wrap.className = "seatmap-canvas-wrap";
  const canvas = document.createElement("canvas");
  canvas.className = "seatmap-canvas";
  wrap.appendChild(canvas);
  root.appendChild(wrap);
  const ctx = canvas.getContext("2d");

  function syncGridInputs() {
    const L = readLayout();
    colsIn.value = String(L.grid.cols);
    rowsIn.value = String(L.grid.rows);
  }
  syncGridInputs();

  function gridToScreen(c, r) {
    const x = offsetX + scale * (PAD + c * CELL);
    const y = offsetY + scale * (PAD + r * CELL);
    return { x: x, y: y, w: scale * CELL - 1, h: scale * CELL - 1 };
  }

  function screenToGrid(sx, sy) {
    const rx = (sx - offsetX) / scale - PAD;
    const ry = (sy - offsetY) / scale - PAD;
    const c = Math.floor(rx / CELL);
    const r = Math.floor(ry / CELL);
    return { c: c, r: r };
  }

  function paintAt(L, c, r) {
    const cols = L.grid.cols;
    const rows = L.grid.rows;
    if (c < 0 || r < 0 || c >= cols || r >= rows) return;
    if (brushT === "e") {
      setCell(L, c, r, { t: "e" });
    } else if (brushT === "a") {
      setCell(L, c, r, { t: "a" });
    } else if (brushT === "st") {
      setCell(L, c, r, { t: "st" });
    } else {
      const prev = getCell(L, c, r);
      const payload = {
        t: "s",
        kind: seatKind,
        row_label: (prev && prev.row_label) || "R",
        seat_number: (prev && prev.seat_number) || "1",
      };
      if (prev && prev.seat_id) {
        payload.seat_id = prev.seat_id;
      }
      setCell(L, c, r, payload);
    }
  }

  function draw() {
    const L = readLayout();
    const cols = L.grid.cols;
    const rows = L.grid.rows;
    const m = cellMap(L);
    const W = offsetX + scale * (PAD * 2 + cols * CELL);
    const H = offsetY + scale * (PAD * 2 + rows * CELL);
    canvas.width = Math.max(400, W + 40);
    canvas.height = Math.max(320, H + 40);
    ctx.fillStyle = "#020617";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    if (L.stage && L.stage.edge === "north") {
      const x0 = offsetX + scale * PAD;
      const y0 = offsetY + scale * 8;
      const w = scale * (cols * CELL);
      ctx.fillStyle = "#334155";
      ctx.fillRect(x0, y0, w, scale * 28);
      ctx.fillStyle = "#f8fafc";
      ctx.font = (14 * scale) + "px Tahoma,Arial";
      ctx.textAlign = "center";
      ctx.fillText(L.stage.label || "صحنه", x0 + w / 2, y0 + scale * 18);
    }
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const cell = m.get(c + "," + r);
        const t = cell ? cell.t : "e";
        const g = gridToScreen(c, r);
        if (t === "e") ctx.fillStyle = "#0f172a";
        else if (t === "a") ctx.fillStyle = "#475569";
        else if (t === "st") ctx.fillStyle = "#64748b";
        else if (t === "s") {
          const k = cell.kind || "standard";
          if (k === "vip") ctx.fillStyle = "#a855f7";
          else if (k === "wheelchair") ctx.fillStyle = "#22c55e";
          else if (k === "blocked") ctx.fillStyle = "#ef4444";
          else ctx.fillStyle = "#3b82f6";
        }
        ctx.fillRect(g.x, g.y, g.w, g.h);
        ctx.strokeStyle = "#1e293b";
        ctx.strokeRect(g.x, g.y, g.w, g.h);
        if (t === "s" && cell && scale > 0.55) {
          ctx.fillStyle = "#fff";
          ctx.font = Math.max(6, 7 * scale) + "px Tahoma";
          ctx.textAlign = "center";
          const lab = (cell.row_label || "") + (cell.seat_number || "");
          ctx.fillText(lab, g.x + g.w / 2, g.y + g.h / 2 + 3);
        }
      }
    }
    selection.forEach(function (key) {
      const p = key.split(",");
      const c = parseInt(p[0], 10);
      const r = parseInt(p[1], 10);
      const g = gridToScreen(c, r);
      ctx.strokeStyle = "#fbbf24";
      ctx.lineWidth = 2;
      ctx.strokeRect(g.x + 1, g.y + 1, g.w - 2, g.h - 2);
    });
    if (selRect) {
      const x0 = Math.min(selRect.c0, selRect.c1);
      const x1 = Math.max(selRect.c0, selRect.c1);
      const y0 = Math.min(selRect.r0, selRect.r1);
      const y1 = Math.max(selRect.r0, selRect.r1);
      const a = gridToScreen(x0, y0);
      const b = gridToScreen(x1, y1);
      ctx.strokeStyle = "#facc15";
      ctx.setLineDash([4, 4]);
      ctx.strokeRect(a.x, a.y, b.x - a.x + b.w, b.y - a.y + b.h);
      ctx.setLineDash([]);
    }
    Array.from(toolbar.querySelectorAll("button[data-tool]")).forEach(function (x) {
      x.classList.toggle("tool-active", x.getAttribute("data-tool") === tool);
    });
  }

  function rectSelect(L, c0, r0, c1, r1) {
    const x0 = Math.min(c0, c1);
    const x1 = Math.max(c0, c1);
    const y0 = Math.min(r0, r1);
    const y1 = Math.max(r0, r1);
    for (let r = y0; r <= y1; r++) {
      for (let c = x0; c <= x1; c++) {
        selection.add(c + "," + r);
      }
    }
  }

  canvas.addEventListener("wheel", function (ev) {
    ev.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const mx = ev.clientX - rect.left;
    const my = ev.clientY - rect.top;
    const before = screenToGrid(mx, my);
    const factor = ev.deltaY < 0 ? 1.08 : 1 / 1.08;
    scale = Math.max(0.35, Math.min(3, scale * factor));
    const after = gridToScreen(before.c, before.r);
    const gx = mx - after.x;
    const gy = my - after.y;
    offsetX += gx;
    offsetY += gy;
    draw();
  }, { passive: false });

  canvas.addEventListener("mousedown", function (ev) {
    const rect = canvas.getBoundingClientRect();
    const mx = ev.clientX - rect.left;
    const my = ev.clientY - rect.top;
    const gr = screenToGrid(mx, my);
    const L = readLayout();
    if (gr.c < 0 || gr.r < 0 || gr.c >= L.grid.cols || gr.r >= L.grid.rows) return;
    isDown = true;
    if (tool === "pan" || spaceDown || ev.button === 1) {
      mode = "pan";
      panFrom = { x: ev.clientX, y: ev.clientY };
      return;
    }
    if (tool === "brush") {
      mode = "brush";
      lastPaint = [gr.c, gr.r];
      paintAt(L, gr.c, gr.r);
      draw();
      return;
    }
    if (tool === "erase") {
      mode = "erase";
      setCell(L, gr.c, gr.r, { t: "e" });
      draw();
      return;
    }
    if (tool === "select") {
      mode = "select";
      selRect = { c0: gr.c, r0: gr.r, c1: gr.c, r1: gr.r };
      if (!ev.shiftKey) selection = new Set();
      draw();
      return;
    }
    if (tool === "move") {
      const k = gr.c + "," + gr.r;
      if (selection.has(k)) {
        mode = "move";
        moveFrom = { c: gr.c, r: gr.r };
      }
    }
  });

  canvas.addEventListener("mousemove", function (ev) {
    const rect = canvas.getBoundingClientRect();
    const mx = ev.clientX - rect.left;
    const my = ev.clientY - rect.top;
    lastMx = mx;
    lastMy = my;
    if (!isDown) return;
    const L = readLayout();
    if (mode === "pan" && panFrom) {
      offsetX += ev.clientX - panFrom.x;
      offsetY += ev.clientY - panFrom.y;
      panFrom = { x: ev.clientX, y: ev.clientY };
      draw();
      return;
    }
    if (mode === "brush" && lastPaint) {
      const gr = screenToGrid(mx, my);
      const line = bresenham(lastPaint[0], lastPaint[1], gr.c, gr.r);
      line.forEach(function (p) {
        paintAt(L, p[0], p[1]);
      });
      lastPaint = [gr.c, gr.r];
      draw();
      return;
    }
    if (mode === "select" && selRect) {
      const gr = screenToGrid(mx, my);
      selRect.c1 = gr.c;
      selRect.r1 = gr.r;
      draw();
      return;
    }
  });

  canvas.addEventListener("mouseup", function () {
    if (!isDown) return;
    isDown = false;
    if (mode === "select" && selRect) {
      const L = readLayout();
      rectSelect(L, selRect.c0, selRect.r0, selRect.c1, selRect.r1);
      selRect = null;
      draw();
    }
    if (mode === "move" && moveFrom) {
      {
        const mx = lastMx;
        const my = lastMy;
        const gr = screenToGrid(mx, my);
        const dc = gr.c - moveFrom.c;
        const dr = gr.r - moveFrom.r;
        if (dc !== 0 || dr !== 0) {
          const L = readLayout();
          const keys = Array.from(selection);
          const targets = keys.map(function (k) {
            const p = k.split(",");
            return [
              parseInt(p[0], 10) + dc,
              parseInt(p[1], 10) + dr,
              k,
            ];
          });
          const m = cellMap(L);
          let ok = true;
          targets.forEach(function (t) {
            const nk = t[0] + "," + t[1];
            if (t[0] < 0 || t[1] < 0 || t[0] >= L.grid.cols || t[1] >= L.grid.rows) ok = false;
            if (m.has(nk) && !selection.has(nk)) ok = false;
          });
          if (ok) {
            const cells = keys
              .map(function (k) {
                const p = k.split(",");
                return getCell(L, parseInt(p[0], 10), parseInt(p[1], 10));
              })
              .filter(Boolean);
            keys.forEach(function (k) {
              const p = k.split(",");
              setCell(L, parseInt(p[0], 10), parseInt(p[1], 10), { t: "e" });
            });
            targets.forEach(function (t, i) {
              const cell = cells[i];
              if (cell) {
                const copy = Object.assign({}, cell);
                delete copy.c;
                delete copy.r;
                setCell(L, t[0], t[1], copy);
              }
            });
            selection = new Set(
              targets.map(function (t) {
                return t[0] + "," + t[1];
              })
            );
          }
        }
      }
      moveFrom = null;
    }
    mode = null;
    panFrom = null;
    lastPaint = null;
    draw();
  });

  window.addEventListener("keydown", function (ev) {
    if (ev.code === "Space") {
      spaceDown = true;
    }
    if (ev.key === "Delete" || ev.key === "Backspace") {
      if (document.activeElement === ta) return;
      const L = readLayout();
      selection.forEach(function (k) {
        const p = k.split(",");
        setCell(L, parseInt(p[0], 10), parseInt(p[1], 10), { t: "e" });
      });
      selection.clear();
      draw();
    }
  });
  window.addEventListener("keyup", function (ev) {
    if (ev.code === "Space") spaceDown = false;
  });

  ta.addEventListener("change", function () {
    syncGridInputs();
    draw();
  });
  draw();
  return true;
  }

  function armSeatmapEditor() {
    if (initSeatmapEditor()) return;
    const obs = new MutationObserver(function () {
      if (initSeatmapEditor()) obs.disconnect();
    });
    obs.observe(document.documentElement, { childList: true, subtree: true });
    let n = 0;
    const iv = setInterval(function () {
      if (initSeatmapEditor()) {
        clearInterval(iv);
        obs.disconnect();
      } else if (++n > 400) {
        clearInterval(iv);
        obs.disconnect();
      }
    }, 25);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", armSeatmapEditor);
  } else {
    armSeatmapEditor();
  }
})();
