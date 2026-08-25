# Auth-Gated App Testing Playbook

## Step 1: Create Test User & Session via MongoDB

```bash
mongosh --eval "
use('test_database');
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({
  user_id: userId,
  email: 'test.user.' + Date.now() + '@example.com',
  name: 'Test User',
  picture: 'https://via.placeholder.com/150',
  created_at: new Date()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"
```

## Step 2: Test Backend APIs

```bash
# Auth
curl -X GET "$URL/api/auth/me" -H "Authorization: Bearer $TOKEN"

# Meals
curl -X POST "$URL/api/meals" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"description":"2 scrambled eggs and a slice of whole wheat toast"}'

curl -X GET "$URL/api/meals" -H "Authorization: Bearer $TOKEN"

# Goals
curl -X GET "$URL/api/goals" -H "Authorization: Bearer $TOKEN"
curl -X PUT "$URL/api/goals" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"calories":2000,"protein":120,"carbs":250,"fat":65}'

# Summary
curl -X GET "$URL/api/nutrition/summary" -H "Authorization: Bearer $TOKEN"

# Suggestions
curl -X POST "$URL/api/suggestions" -H "Authorization: Bearer $TOKEN"
```

## Step 3: Browser Testing

Use Playwright: add cookie `session_token` with `httpOnly=true`, `secure=true`, `sameSite=None`, then navigate to /dashboard.

## Success Indicators
- /api/auth/me returns user data (200)
- Dashboard loads without redirect
- Meal analysis returns structured nutrition JSON
