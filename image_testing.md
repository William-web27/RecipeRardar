# Image Integration Testing Playbook

## Rules
- Always use base64-encoded images (JPEG or PNG only)
- Real photos with visual features (no solid color / blank images)
- Endpoint: POST /api/meals/photo with JSON body `{"image_base64": "<b64 without data: prefix>", "mime_type": "image/jpeg", "hint": "optional text"}`
- Expected response mirrors the text meal endpoint: `id`, `description`, `nutrients`, `summary`, `healthiness_score`, `tags`

## Quick curl test
```bash
IMG=$(base64 -w 0 /tmp/lunch.jpg)
curl -X POST "$URL/api/meals/photo" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"image_base64\":\"$IMG\",\"mime_type\":\"image/jpeg\"}"
```
