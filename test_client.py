import asyncio
import websockets
import json

async def test():
    uri = "wss://chargerpulse-1.onrender.com/TestCharger123"
    async with websockets.connect(uri, subprotocols=['ocpp1.6']) as websocket:
        print("✅ Connected!")
        
        # Send a test message
        msg = [2, "123", "StatusNotification", {"connectorId": 1, "status": "Available"}]
        await websocket.send(json.dumps(msg))
        print(f"✅ Sent: {msg}")
        
        # Receive response
        response = await websocket.recv()
        print(f"📨 Received: {response}")

asyncio.run(test())