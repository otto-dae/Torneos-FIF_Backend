from django.db import models


class Administrator(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    email = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=255)

    class Meta:
        db_table = 'administrators' 
        managed = False              

    def __str__(self):
        return self.name