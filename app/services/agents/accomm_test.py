import http.client
import json

 conn = http.client.HTTPSConnection("google.serper.dev")

payload = json.dumps({
"q": f"{location}숙소",
'll': f"@{location_coordinates},15.1z", 
"gl": "kr",
"hl": "ko"
})
headers = {
'X-API-KEY': 'a8c775ccdc443e339ea7092b92af166a6163fa1f',
'Content-Type': 'application/json'
}
conn.request("POST", "/maps", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))