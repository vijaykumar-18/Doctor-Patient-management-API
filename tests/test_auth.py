def test_register_and_login(client):
    # Register doctor user
    reg_res = client.post("/api/v1/auth/register", json={
        "email": "doctor_doc@test.com",
        "password": "strongpassword123",
        "role": "doctor"
    })
    assert reg_res.status_code == 201
    assert reg_res.json()["email"] == "doctor_doc@test.com"

    # Login
    login_res = client.post("/api/v1/auth/token", data={
        "username": "doctor_doc@test.com",
        "password": "strongpassword123"
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()