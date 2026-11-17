"""Bridge: Tobii *Pro* SDK eye tracker -> WebSocket (ws://localhost:8765) for Gaze Reader.

Works with trackers supported by the Tobii Pro SDK (pip install tobii-research websockets).
The consumer Tobii Eye Tracker 5 is NOT supported by the Pro SDK; it needs Tobii's Game Integration API
(a C#/C++ program that sends the same JSON). Tobii's consumer licence also restricts storing gaze data, so keep
Gaze Reader's recording off when using one.

Messages sent (per eye, screen fractions 0..1, null when that eye isn't tracked):
    {"l": [x, y] | null, "r": [x, y] | null}

Run:  python tobii_pro_bridge.py          (or  --mouse  to send the mouse position instead, to test the pipe)
Then in Gaze Reader: Settings -> External eye tracker address = ws://localhost:8765 -> "Use external eye tracker".
"""
import asyncio, json, sys, threading

latest = {"l": None, "r": None}
clients = set()

def on_gaze(g):
    def eye(side):
        if g.get(f"{side}_gaze_point_validity"):
            x, y = g[f"{side}_gaze_point_on_display_area"]
            return [x, y]
        return None
    latest["l"], latest["r"] = eye("left"), eye("right")

def start_tobii():
    import tobii_research as tr
    trackers = tr.find_all_eyetrackers()
    if not trackers:
        sys.exit("No Tobii Pro tracker found.")
    t = trackers[0]
    print("Using", t.model, t.serial_number)
    t.subscribe_to(tr.EYETRACKER_GAZE_DATA, on_gaze, as_dictionary=True)

def start_mouse():
    import tkinter as tk
    root = tk.Tk(); root.withdraw()
    W, H = root.winfo_screenwidth(), root.winfo_screenheight()
    def loop():
        while True:
            x, y = root.winfo_pointerxy()
            latest["l"] = latest["r"] = [x / W, y / H]
            threading.Event().wait(1 / 60)
    threading.Thread(target=loop, daemon=True).start()

async def handler(ws):
    clients.add(ws)
    try:
        await ws.wait_closed()
    finally:
        clients.discard(ws)

async def pump():
    while True:
        if clients:
            msg = json.dumps(latest)
            await asyncio.gather(*(c.send(msg) for c in list(clients)), return_exceptions=True)
        await asyncio.sleep(1 / 60)

async def main():
    import websockets
    (start_mouse if "--mouse" in sys.argv else start_tobii)()
    async with websockets.serve(handler, "localhost", 8765):
        print("Gaze bridge on ws://localhost:8765")
        await pump()

if __name__ == "__main__":
    asyncio.run(main())
