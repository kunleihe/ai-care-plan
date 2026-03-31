from django.db import models


class Patient(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    mrn = models.CharField(max_length=20, unique=True)
    dob = models.DateField()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.mrn})"


class Provider(models.Model):
    name = models.CharField(max_length=200)
    npi = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return f"{self.name} (NPI: {self.npi})"


class Order(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='orders')
    provider = models.ForeignKey(Provider, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    referring_provider_name = models.CharField(max_length=200, blank=True)
    medication = models.CharField(max_length=200)
    diagnosis = models.CharField(max_length=20)  # ICD-10 code
    medical_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.pk} - {self.patient} / {self.medication}"


class CarePlan(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='care_plan')
    content = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CarePlan #{self.pk} [{self.status}] - Order #{self.order_id}"
