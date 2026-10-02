def test_create_patient_validation(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Fail with short phone number
    bad_res = client.post("/api/v1/patients", json={
        "name": "John Doe",
        "age": 30,
        "phone": "123"
    }, headers=headers)
    assert bad_res.status_code == 422

    # Success with 10 digit number
    good_res = client.post("/api/v1/patients", json={
        "name": "John Doe",
        "age": 30,
        "phone": "9876543210"
    }, headers=headers)
    assert good_res.status_code == 201