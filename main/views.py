from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
import json
import jwt
import datetime
from django.conf import settings
from .models import Administrator, Discipline, Tournament, Team, Participant, Match, Log


def index(request):
    return HttpResponse("Tournament API is running.")


@csrf_exempt
@require_POST
def login(request):
    try:
        body = json.loads(request.body)
        email = body.get('email', '').strip()
        password = body.get('password', '').strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    if not email or not password:
        return JsonResponse({'error': 'Email and password are required'}, status=400)

    try:
        admin = Administrator.objects.get(email=email, password=password)
    except Administrator.DoesNotExist:
        return JsonResponse({'error': 'Invalid credentials'}, status=401)

    payload = {
        'id': admin.id,
        'name': admin.name,
        'email': admin.email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=8),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    return JsonResponse({
        'token': token,
        'admin': {
            'id': admin.id,
            'name': admin.name,
            'email': admin.email,
        }
    }, status=200)


@require_GET
def get_disciplines(request):
    disciplines = Discipline.objects.all()
    data = [{'id': d.id, 'name': d.name} for d in disciplines]
    return JsonResponse(data, safe=False)


@require_GET
def get_tournaments(request):
    tournaments = Tournament.objects.select_related('discipline').all()
    data = [
        {
            'id': t.id,
            'name': t.name,
            'noteams': t.noteams,
            'matchdays': t.matchdays,
            'discipline': t.discipline.name,
            'discipline_id': t.discipline.id,
        }
        for t in tournaments
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_POST
def create_tournament(request):
    try:
        body = json.loads(request.body)
        name = body.get('name', '').strip()
        noteams = body.get('noteams')
        matchdays = body.get('matchdays')
        discipline_id = body.get('discipline_id')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    if not name or not noteams or not matchdays or not discipline_id:
        return JsonResponse({'error': 'All fields are required'}, status=400)

    try:
        discipline = Discipline.objects.get(id=discipline_id)
    except Discipline.DoesNotExist:
        return JsonResponse({'error': 'Discipline not found'}, status=404)

    tournament = Tournament.objects.create(
        name=name,
        noteams=noteams,
        matchdays=matchdays,
        discipline=discipline,
    )

    return JsonResponse({
        'id': tournament.id,
        'name': tournament.name,
        'noteams': tournament.noteams,
        'matchdays': tournament.matchdays,
        'discipline': discipline.name,
    }, status=201)


@require_GET
def get_teams(request):
    tournament_id = request.GET.get('tournament_id')
    teams = Team.objects.select_related('tournament__discipline').all()
    if tournament_id:
        teams = teams.filter(tournament_id=tournament_id)
    data = [
        {
            'id': t.id,
            'name': t.name,
            'logo': t.logo,
            'pj': t.pj,
            'pg': t.pg,
            'pe': t.pe,
            'pp': t.pp,
            'gf': t.gf,
            'gc': t.gc,
            'points': t.points,
            'tournament': t.tournament.name,
            'tournament_id': t.tournament.id,
            'discipline': t.tournament.discipline.name,
        }
        for t in teams
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_POST
def create_team(request):
    try:
        body = json.loads(request.body)
        name = body.get('name', '').strip()
        logo = body.get('logo', '').strip()
        tournament_id = body.get('tournament_id')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    if not name or not tournament_id:
        return JsonResponse({'error': 'Name and tournament are required'}, status=400)

    try:
        tournament = Tournament.objects.get(id=tournament_id)
    except Tournament.DoesNotExist:
        return JsonResponse({'error': 'Tournament not found'}, status=404)

    team = Team.objects.create(
        name=name,
        logo=logo,
        tournament=tournament,
    )

    return JsonResponse({
        'id': team.id,
        'name': team.name,
        'logo': team.logo,
        'tournament': tournament.name,
    }, status=201)

@require_GET
def get_participants(request):
    team_id = request.GET.get('team_id')
    participants = Participant.objects.select_related('team').all()
    if team_id:
        participants = participants.filter(team_id=team_id)
    data = [
        {
            'id': p.id,
            'name': p.name,
            'phone': p.phone,
            'email': p.email,
            'team': p.team.name,
            'team_id': p.team.id,
        }
        for p in participants
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_POST
def create_participant(request):
    try:
        body = json.loads(request.body)
        name = body.get('name', '').strip()
        phone = body.get('phone', '').strip()
        email = body.get('email', '').strip()
        team_id = body.get('team_id')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    if not name or not team_id:
        return JsonResponse({'error': 'Name and team are required'}, status=400)

    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        return JsonResponse({'error': 'Team not found'}, status=404)

    participant = Participant.objects.create(
        name=name,
        phone=phone,
        email=email,
        team=team,
    )

    return JsonResponse({
        'id': participant.id,
        'name': participant.name,
        'phone': participant.phone,
        'email': participant.email,
        'team': team.name,
    }, status=201)

@require_GET
def get_matches(request):
    tournament_id = request.GET.get('tournament_id')
    matches = Match.objects.select_related('team_1', 'team_2', 'tournament').all()
    if tournament_id:
        matches = matches.filter(tournament_id=tournament_id)
    data = [
        {
            'id': m.id,
            'tournament': m.tournament.name,
            'tournament_id': m.tournament.id,
            'team_1': m.team_1.name,
            'team_1_id': m.team_1.id,
            'team_2': m.team_2.name,
            'team_2_id': m.team_2.id,
            'gf': m.gf,
            'gc': m.gc,
            'datematch': str(m.datematch) if m.datematch else None,
        }
        for m in matches
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_POST
def generate_matches(request):
    try:
        body = json.loads(request.body)
        tournament_id = body.get('tournament_id')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    if not tournament_id:
        return JsonResponse({'error': 'tournament_id is required'}, status=400)

    try:
        tournament = Tournament.objects.get(id=tournament_id)
    except Tournament.DoesNotExist:
        return JsonResponse({'error': 'Tournament not found'}, status=404)

    if Match.objects.filter(tournament_id=tournament_id).exists():
        return JsonResponse({'error': 'Matches already generated for this tournament'}, status=400)

    teams = list(Team.objects.filter(tournament_id=tournament_id))

    if len(teams) < 2:
        return JsonResponse({'error': 'Not enough teams'}, status=400)

    matches_created = []
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            match = Match.objects.create(
                tournament=tournament,
                team_1=teams[i],
                team_2=teams[j],
            )
            matches_created.append({
                'id': match.id,
                'team_1': teams[i].name,
                'team_2': teams[j].name,
            })

    return JsonResponse({'matches': matches_created}, status=201)

@csrf_exempt
@require_POST
def update_match(request, match_id):
    try:
        body = json.loads(request.body)
        gf = body.get('gf')
        gc = body.get('gc')
        datematch = body.get('datematch')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    try:
        match = Match.objects.get(id=match_id)
    except Match.DoesNotExist:
        return JsonResponse({'error': 'Match not found'}, status=404)

    if datematch:
        match.datematch = datematch

    if gf is not None and gc is not None:
        if match.gf is not None:
            return JsonResponse({'error': 'Match already has a result'}, status=400)

        match.gf = gf
        match.gc = gc

        team_1 = match.team_1
        team_2 = match.team_2

        team_1.pj += 1
        team_2.pj += 1

        if gf > gc:
            team_1.pg += 1
            team_1.points += 3
            team_2.pp += 1
        elif gf < gc:
            team_2.pg += 1
            team_2.points += 3
            team_1.pp += 1
        else:
            team_1.pe += 1
            team_2.pe += 1
            team_1.points += 1
            team_2.points += 1

        team_1.gf += gf
        team_1.gc += gc
        team_2.gf += gc
        team_2.gc += gf

        team_1.save()
        team_2.save()

    match.save()

    return JsonResponse({
        'id': match.id,
        'gf': match.gf,
        'gc': match.gc,
        'datematch': str(match.datematch) if match.datematch else None,
    }, status=200)

@csrf_exempt
@require_POST
def logout(request):
    return JsonResponse({'message': 'Logged out'}, status=200)