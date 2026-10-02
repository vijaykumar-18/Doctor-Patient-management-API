from datetime import datetime, timedelta

def test_prevent_overlapping_appointments(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Setup doctor & patient
    doc = client.post("/api/v1/doctors", json={"name": "Dr. House", "email": "house@med.com", "specialization": "Diagnostics"}, headers=headers).json()
    pat = client.post("/api/v1/patients", json={"name": "Patient X", "age": 45, "phone": "1234567890"}, headers=headers).json()

    slot = (datetime.utcnow() + timedelta(days=1)).isoformat()

    # First appointment succeeds
    res1 = client.post("/api/v1/appointments", json={"doctor_id": doc["id"], "patient_id": pat["id"], "appointment_date": slot}, headers=headers)
    assert res1.status_code == 201

    # Overlapping appointment must fail
    res2 = client.post("/api/v1/appointments", json={"doctor_id": doc["id"], "patient_id": pat["id"], "appointment_date": slot}, headers=headers)
    assert res2.status_code == 400