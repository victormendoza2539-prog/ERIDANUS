from locust import HttpUser, task, between

class UsuarioTienditaCompleto(HttpUser):
    wait_time = between(0.2, 0.8)

    @task(3)
    def comprarProducto(self):
        with self.client.post("/productos/3", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 400:
                response.success()
            else:
                response.failure(f"Falla inesperada con código {response.status_code}")

    @task(2)
    def getProducto(self):
        self.client.get("/")

    @task(1)
    def getCatalogo(self):
        self.client.get("/productos")