import unittest
from fastapi.testclient import TestClient
from app import app
import base64
import os

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.valid_pdf_data = base64.b64encode(b"This is a dummy PDF content").decode('utf-8')

    def test_save_url_valid(self):
        payload = {"url": "https://www.example.com"}
        response = self.client.post("/save_url", json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"message": "Success!"})

    def test_save_url_invalid(self):
        payload = {"url": "not-a-url"}
        response = self.client.post("/save_url", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Invalid URL format."})

    def test_upload_invalid_data_bad_request(self):
        payload = {"data": "This should be a dict."}
        response = self.client.post("/upload_pdf", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Invalid JSON format. Expected a dict with a 'pdf_binary' field."})

    def test_upload_valid_data_success(self):
        payload = {
            "pdf_binary": self.valid_pdf_data,
            "filename": "test.pdf"
        }
        response = self.client.post("/upload_pdf", json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"message": "Success!"})

    def test_upload_non_base64_data_bad_request(self):
        payload = {
            "pdf_binary": "Not base64 data",
            "filename": "test.pdf"
        }
        response = self.client.post("/upload_pdf", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Invalid base64 string."})

    def test_get_document_success(self):
        filename = "test_get.pdf"
        with open(filename, "wb") as f:
            f.write(b"Test PDF content")
            
        response = self.client.get(f"/get_document/{filename}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'application/pdf')
        
        if os.path.exists(filename):
            os.remove(filename)

    def test_get_document_not_found(self):
        response = self.client.get("/get_document/nonexistent.pdf")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Document not found."})

    def test_delete_document_success(self):
        filename = "test_delete.pdf"
        with open(filename, "wb") as f:
            f.write(b"Delete me")
            
        response = self.client.post(f"/delete_document/{filename}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Success!"})

    def test_delete_document_not_found(self):
        response = self.client.post("/delete_document/nonexistent.pdf")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Document not found."})

if __name__ == '__main__':
    unittest.main()
