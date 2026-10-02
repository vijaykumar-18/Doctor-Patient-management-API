def test_create_and_get_doctor(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    create_res = client.post("/api/v1/doctors", json={
        "name": "Dr. Strange",
        "email": "strange@marvel.com",
        "specialization": "Neurosurgeon"
    }, headers=headers)
    assert create_res.status_code == 201
    doc_id = create_res.json()["id"]

    get_res = client.get(f"/api/v1/doctors/{doc_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Dr. Strange"