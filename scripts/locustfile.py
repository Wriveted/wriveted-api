"""
Setup: Install all project deps with `poetry install`
Set the environment variable `WRIVETED_API_TOKEN`
Run: `poetry -m locust` in terminal.
Open http://localhost:8089 and run a test setting the target to your local API: http://localhost:8000/v1
"""
import os
import random

from locust import HttpUser, between, task


class User(HttpUser):

    # make the simulated users wait between 0.5 and 2 seconds after each task
    wait_time = between(0.5, 2)

    def on_start(self):
        self.access_token = os.environ.get("WRIVETED_API_TOKEN")

    @task
    def test_token(self):
        self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )

    @task
    def get_users_and_details(self):
        users_list_response = self.client.get(
            "/users",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        users_list_response.raise_for_status()
        user_briefs = users_list_response.json()

        for user_brief in user_briefs:
            if random.random() > 0.8:

                user_detail_response = self.client.get(
                    f"/user/{user_brief['id']}",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )
                user_detail_response.json()

    @task
    def get_booklists_and_details(self):
        list_response = self.client.get(
            "/lists",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        list_response.raise_for_status()
        list_briefs = list_response.json()["data"]

        for list_brief in list_briefs:
            if random.random() > 0.8:

                list_detail_response = self.client.get(
                    f"/list/{list_brief['id']}",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )
                list_detail_response.json()

    @task
    def get_version(self):
        self.client.get("/version").json()
