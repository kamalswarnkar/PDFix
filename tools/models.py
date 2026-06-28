from django.db import models


class Feedback(models.Model):
    feature = models.CharField(max_length=150)
    issue = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback [{self.feature}] @ {self.submitted_at:%Y-%m-%d %H:%M}"


class Suggestion(models.Model):
    description = models.TextField()
    why_needed = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Suggestion @ {self.submitted_at:%Y-%m-%d %H:%M}"
