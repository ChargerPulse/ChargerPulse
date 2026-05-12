import asyncio
import websockets
import json
import random
from datetime import datetime

OCPP_SERVER_URL = "wss://chargerpulse-1.onrender.com"  # Your live server
CHARGER_ID = "RealCharger001"

async def connect_charger():
    """Simulate a real EV charger connecting and sending status updates"""
    uri = f"{OCPP_SERVER_URL}/{CHARGER_ID}"
    
    async with websockets.connect(uri, subprotocols=['ocpp1.6']) as websocket:
        print(f"✅ Connected: {CHARGER_ID}")
        
        # Send initial status
        initial_status = [2, "1", "StatusNotification", {
            "connectorId": 1,
            "status": "Available",
            "timestamp": datetime.utcnow().isoformat()
        }]
        await websocket.send(json.dumps(initial_status))
        print(f"📤 Sent initial status: Available")
        
        # Simulate charger activity for 2 minutes
        for i in range(12):  # 12 updates = 2 minutes (10 sec each)
            await asyncio.sleep(10)
            
            # Randomly switch between Available, Occupied, Faulted
            statuses = ["Available", "Occupied", "Available", "Available"]
            status = random.choice(statuses)
            
            message = [2, str(i+2), "StatusNotification", {
                "connectorId": 1,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }]
            
            await websocket.send(json.dumps(message))
            print(f"📤 Sent status: {status}")
            
            # Receive acknowledgment
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                print(f"📨 Received: {response[:50]}...")
            except asyncio.TimeoutError:
                print("⏱️  No response (that's okay)")
        
        print("✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(connect_charger())