import asyncio
import websockets
import json
import datetime

async def connect_charger():
    uri = "wss://chargerpulse-1.onrender.com/RealCharger001"
    
    print("Connecting to OCPP server...")
    async with websockets.connect(uri, subprotocols=['ocpp1.6']) as websocket:
        print("✅ Connected: RealCharger001")
        
        msg_id = 1
        
        async def send_status(status):
            nonlocal msg_id
            message = json.dumps([
                2, str(msg_id), "StatusNotification",
                {
                    "connectorId": 1,
                    "status": status,
                    "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
                }
            ])
            await websocket.send(message)
            print(f"📤 Sent status: {status}")
            msg_id += 1
            response = await websocket.recv()
            print(f"📨 Received: {response[:60]}")
            await asyncio.sleep(2)

        # Normal operation
        await send_status("Available")
        await send_status("Available")
        
        # Charger breaks! 🚨
        print("\n🚨 Simulating charger fault...")
        await send_status("Faulted")
        await send_status("Faulted")
        
        # Charger recovers ✅
        print("\n✅ Simulating charger recovery...")
        await send_status("Available")
        await send_status("Available")

asyncio.run(connect_charger())