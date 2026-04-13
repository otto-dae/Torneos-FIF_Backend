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


class Discipline(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)

    class Meta:
        db_table = 'disciplines'
        managed = False

    def __str__(self):
        return self.name


class Tournament(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    noteams = models.SmallIntegerField()
    matchdays = models.SmallIntegerField()
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE, db_column='disciplineid')

    class Meta:
        db_table = 'tournaments'
        managed = False

    def __str__(self):
        return self.name


class Team(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    logo = models.TextField(blank=True, null=True)
    pj = models.SmallIntegerField(default=0)
    pg = models.SmallIntegerField(default=0)
    pe = models.SmallIntegerField(default=0)
    pp = models.SmallIntegerField(default=0)
    gf = models.SmallIntegerField(default=0)
    gc = models.SmallIntegerField(default=0)
    points = models.SmallIntegerField(default=0)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, db_column='tournamentid')

    class Meta:
        db_table = 'teams'
        managed = False

    def __str__(self):
        return self.name


class Participant(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=255, blank=True, null=True)
    ssn = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, db_column='teamid')

    class Meta:
        db_table = 'participants'
        managed = False

    def __str__(self):
        return self.name


class Match(models.Model):
    id = models.AutoField(primary_key=True)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, db_column='tournamentid')
    team_1 = models.ForeignKey(Team, on_delete=models.CASCADE, db_column='team_1id', related_name='home_matches')
    team_2 = models.ForeignKey(Team, on_delete=models.CASCADE, db_column='team_2id', related_name='away_matches')
    gf = models.SmallIntegerField(blank=True, null=True)
    gc = models.SmallIntegerField(blank=True, null=True)
    df = models.SmallIntegerField(blank=True, null=True)
    datematch = models.DateField(blank=True, null=True)

    class Meta:
        db_table = 'matches'
        managed = False

    def __str__(self):
        return f"{self.team_1} vs {self.team_2}"


class Log(models.Model):
    id = models.AutoField(primary_key=True)
    action = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    administrator = models.ForeignKey(Administrator, on_delete=models.CASCADE, db_column='administratorid')

    class Meta:
        db_table = 'logs'
        managed = False

    def __str__(self):
        return self.action