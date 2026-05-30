from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
import json
import jwt
import datetime
from django.conf import settings
from .models import Administrator, Discipline, Tournament, Team, Participant, Match, Log, Phase, PhaseMatch

def admin_required(func):
    def wrapper(request, *args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return JsonResponse({'error': 'No token provided'}, status=401)
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            request.admin_id = payload.get('id')
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({'error': 'Invalid token'}, status=401)
        return func(request, *args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


def create_log(action: str, admin_id: int):
    try:
        admin = Administrator.objects.get(id=admin_id)
        Log.objects.create(action=action, administrator=admin)
    except Administrator.DoesNotExist:
        pass


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


@csrf_exempt
@require_POST
def logout(request):
    return JsonResponse({'message': 'Logged out'}, status=200)


@require_GET
def get_disciplines(request):
    disciplines = Discipline.objects.all()
    data = [{'id': d.id, 'name': d.name} for d in disciplines]
    return JsonResponse(data, safe=False)


@require_GET
def get_tournaments(request):
    tournaments = Tournament.objects.select_related('discipline', 'winner').all()
    data = [
        {
            'id': t.id,
            'name': t.name,
            'noteams': t.noteams,
            'matchdays': t.matchdays,
            'discipline': t.discipline.name,
            'discipline_id': t.discipline.id,
            'phase_started': t.phase_started,
            'finished': t.finished,
            'winner': t.winner.name if t.winner else None,
        }
        for t in tournaments
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_POST
@admin_required
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

    create_log(f'Torneo {tournament.name} fue creado', request.admin_id)

    return JsonResponse({
        'id': tournament.id,
        'name': tournament.name,
        'noteams': tournament.noteams,
        'matchdays': tournament.matchdays,
        'discipline': discipline.name,
    }, status=201)

@csrf_exempt
@require_POST
@admin_required
def finish_tournament(request, tournament_id):
    try:
        tournament = Tournament.objects.get(id=tournament_id)
    except Tournament.DoesNotExist:
        return JsonResponse({'error': 'Tournament not found'}, status=404)

    if not tournament.phase_started:
        return JsonResponse({'error': 'Elimination phase has not started'}, status=400)

    if tournament.finished:
        return JsonResponse({'error': 'Tournament already finished'}, status=400)

    last_phase = Phase.objects.filter(tournament_id=tournament_id).order_by('-phase_order').first()
    if not last_phase:
        return JsonResponse({'error': 'No phases found'}, status=400)

    phase_matches = PhaseMatch.objects.filter(phase=last_phase)

    if not all(m.gf is not None for m in phase_matches):
        return JsonResponse({'error': 'Not all matches have results'}, status=400)

    if phase_matches.count() != 1:
        return JsonResponse({'error': 'Final match not yet played'}, status=400)

    final = phase_matches.first()
    if final.gf > final.gc:
        winner = final.team_1
    else:
        winner = final.team_2

    tournament.finished = True
    tournament.winner = winner
    tournament.save()

    create_log(f'Torneo {tournament.name} finalizado. Campeon: {winner.name}', request.admin_id)

    return JsonResponse({
        'winner': winner.name,
        'tournament': tournament.name,
    }, status=200)

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
@admin_required
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

    current_teams = Team.objects.filter(tournament_id=tournament_id).count()
    if current_teams >= tournament.noteams:
        return JsonResponse({'error': f'Tournament already has {tournament.noteams} teams'}, status=400)

    team = Team.objects.create(
        name=name,
        logo=logo,
        tournament=tournament,
    )

    create_log(f'Equipo {team.name} fue agregado al torneo {tournament.name}', request.admin_id)

    new_count = current_teams + 1
    matches_generated = False

    if new_count >= tournament.noteams and not Match.objects.filter(tournament_id=tournament_id).exists():
        teams = list(Team.objects.filter(tournament_id=tournament_id))
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                Match.objects.create(
                    tournament=tournament,
                    team_1=teams[i],
                    team_2=teams[j],
                )
        matches_generated = True
        create_log(f'Calendario generado automaticamente para el torneo {tournament.name}', request.admin_id)

    return JsonResponse({
        'id': team.id,
        'name': team.name,
        'logo': team.logo,
        'tournament': tournament.name,
        'matches_generated': matches_generated,
        'teams_count': new_count,
        'teams_required': tournament.noteams,
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
@admin_required
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

    create_log(f'Participante {participant.name} fue agregado al equipo {team.name}', request.admin_id)

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
@admin_required
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

    create_log(f'Calendario generado para el torneo {tournament.name}', request.admin_id)

    return JsonResponse({'matches': matches_created}, status=201)


@csrf_exempt
@require_POST
@admin_required
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
        team_1 = match.team_1
        team_2 = match.team_2

        if match.gf is not None:
            old_gf = match.gf
            old_gc = match.gc

            team_1.pj -= 1
            team_2.pj -= 1
            team_1.gf -= old_gf
            team_1.gc -= old_gc
            team_2.gf -= old_gc
            team_2.gc -= old_gf

            if old_gf > old_gc:
                team_1.pg -= 1
                team_1.points -= 3
                team_2.pp -= 1
            elif old_gf < old_gc:
                team_2.pg -= 1
                team_2.points -= 3
                team_1.pp -= 1
            else:
                team_1.pe -= 1
                team_2.pe -= 1
                team_1.points -= 1
                team_2.points -= 1

        match.gf = gf
        match.gc = gc

        team_1.pj += 1
        team_2.pj += 1
        team_1.gf += gf
        team_1.gc += gc
        team_2.gf += gc
        team_2.gc += gf

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

        team_1.save()
        team_2.save()

        create_log(f'Partido {match.team_1} vs {match.team_2} actualizado: {gf} - {gc}', request.admin_id)

    match.save()

    return JsonResponse({
        'id': match.id,
        'gf': match.gf,
        'gc': match.gc,
        'datematch': str(match.datematch) if match.datematch else None,
    }, status=200)


@require_GET
def get_logs(request):
    logs = Log.objects.select_related('administrator').order_by('-date')
    data = [
        {
            'id': l.id,
            'action': l.action,
            'date': str(l.date),
            'admin': l.administrator.name,
        }
        for l in logs
    ]
    return JsonResponse(data, safe=False)

@csrf_exempt
@require_POST
@admin_required
def create_administrator(request):
    try:
        body = json.loads(request.body)
        name = body.get('name', '').strip()
        email = body.get('email', '').strip()
        password = body.get('password', '').strip()
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    if not name or not email or not password:
        return JsonResponse({'error': 'All fields are required'}, status=400)

    if Administrator.objects.filter(email=email).exists():
        return JsonResponse({'error': 'Email already exists'}, status=400)

    admin = Administrator.objects.create(
        name=name,
        email=email,
        password=password,
    )

    create_log(f'Admin {admin.name} fue creado', request.admin_id)

    return JsonResponse({
        'id': admin.id,
        'name': admin.name,
        'email': admin.email,
    }, status=201)


@csrf_exempt
@require_POST
@admin_required
def start_phase(request, tournament_id):
    try:
        tournament = Tournament.objects.get(id=tournament_id)
    except Tournament.DoesNotExist:
        return JsonResponse({'error': 'Tournament not found'}, status=404)

    if tournament.phase_started:
        return JsonResponse({'error': 'Phase already started'}, status=400)

    teams = Team.objects.filter(tournament_id=tournament_id).order_by('-points', '-gf')
    total = teams.count()

    if total < 4:
        return JsonResponse({'error': 'Need at least 4 teams to start elimination phase'}, status=400)

    if total >= 16:
        slots = 16
        phase_name = 'Octavos de Final'
    elif total >= 8:
        slots = 8
        phase_name = 'Cuartos de Final'
    else:
        slots = 4
        phase_name = 'Semifinales'

    top_teams = list(teams[:slots])

    phase = Phase.objects.create(
        tournament=tournament,
        name=phase_name,
        phase_order=1,
    )

    mid = slots // 2
    for i in range(mid):
        PhaseMatch.objects.create(
            phase=phase,
            team_1=top_teams[i],
            team_2=top_teams[slots - 1 - i],
        )

    tournament.phase_started = True
    tournament.save()

    create_log(f'Fase eliminatoria iniciada en torneo {tournament.name}: {phase_name}', request.admin_id)

    return JsonResponse({
        'phase': phase_name,
        'matches': [
            {
                'team_1': top_teams[i].name,
                'team_2': top_teams[slots - 1 - i].name,
            }
            for i in range(mid)
        ]
    }, status=201)


@require_GET
def get_phases(request, tournament_id):
    phases = Phase.objects.filter(tournament_id=tournament_id).order_by('phase_order')
    data = []
    for phase in phases:
        matches = PhaseMatch.objects.select_related('team_1', 'team_2').filter(phase=phase)
        data.append({
            'id': phase.id,
            'name': phase.name,
            'phase_order': phase.phase_order,
            'matches': [
                {
                    'id': m.id,
                    'team_1': m.team_1.name if m.team_1 else 'TBD',
                    'team_1_id': m.team_1.id if m.team_1 else None,
                    'team_2': m.team_2.name if m.team_2 else 'TBD',
                    'team_2_id': m.team_2.id if m.team_2 else None,
                    'gf': m.gf,
                    'gc': m.gc,
                    'datematch': str(m.datematch) if m.datematch else None,
                }
                for m in matches
            ]
        })
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_POST
@admin_required
def start_phase(request, tournament_id):
    try:
        tournament = Tournament.objects.get(id=tournament_id)
    except Tournament.DoesNotExist:
        return JsonResponse({'error': 'Tournament not found'}, status=404)

    if tournament.phase_started:
        return JsonResponse({'error': 'Phase already started'}, status=400)

    teams = Team.objects.filter(tournament_id=tournament_id).order_by('-points', '-gf')
    total = teams.count()

    if total < 4:
        return JsonResponse({'error': 'Need at least 4 teams to start elimination phase'}, status=400)

    if total >= 16:
        slots = 16
        phase_name = 'Octavos de Final'
    elif total >= 8:
        slots = 8
        phase_name = 'Cuartos de Final'
    else:
        slots = 4
        phase_name = 'Semifinales'

    top_teams = list(teams[:slots])

    phase = Phase.objects.create(
        tournament=tournament,
        name=phase_name,
        phase_order=1,
    )

    mid = slots // 2
    for i in range(mid):
        PhaseMatch.objects.create(
            phase=phase,
            team_1=top_teams[i],
            team_2=top_teams[slots - 1 - i],
        )

    tournament.phase_started = True
    tournament.save()

    create_log(f'Fase eliminatoria iniciada en torneo {tournament.name}: {phase_name}', request.admin_id)

    return JsonResponse({
        'phase': phase_name,
        'matches': [
            {
                'team_1': top_teams[i].name,
                'team_2': top_teams[slots - 1 - i].name,
            }
            for i in range(mid)
        ]
    }, status=201)


@require_GET
def get_phases(request, tournament_id):
    phases = Phase.objects.filter(tournament_id=tournament_id).order_by('phase_order')
    data = []
    for phase in phases:
        matches = PhaseMatch.objects.select_related('team_1', 'team_2').filter(phase=phase)
        data.append({
            'id': phase.id,
            'name': phase.name,
            'phase_order': phase.phase_order,
            'matches': [
                {
                    'id': m.id,
                    'team_1': m.team_1.name if m.team_1 else 'TBD',
                    'team_1_id': m.team_1.id if m.team_1 else None,
                    'team_2': m.team_2.name if m.team_2 else 'TBD',
                    'team_2_id': m.team_2.id if m.team_2 else None,
                    'gf': m.gf,
                    'gc': m.gc,
                    'datematch': str(m.datematch) if m.datematch else None,
                }
                for m in matches
            ]
        })
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_POST
@admin_required
def update_phase_match(request, match_id):
    try:
        body = json.loads(request.body)
        gf = body.get('gf')
        gc = body.get('gc')
        datematch = body.get('datematch')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    try:
        match = PhaseMatch.objects.select_related('phase__tournament').get(id=match_id)
    except PhaseMatch.DoesNotExist:
        return JsonResponse({'error': 'Match not found'}, status=404)

    if datematch:
        match.datematch = datematch

    if gf is not None and gc is not None:
        if gf == gc:
            return JsonResponse({'error': 'Elimination matches cannot end in a draw'}, status=400)
        match.gf = gf
        match.gc = gc
        create_log(f'Partido eliminatorio {match.team_1} vs {match.team_2} actualizado: {gf} - {gc}', request.admin_id)

    match.save()

    phase = match.phase
    phase_matches = PhaseMatch.objects.filter(phase=phase)
    all_done = all(m.gf is not None for m in phase_matches)

    if all_done:
        winners = []
        for m in phase_matches:
            if m.gf > m.gc:
                winners.append(m.team_1)
            else:
                winners.append(m.team_2)

        if len(winners) == 1:
            create_log(f'Campeon del torneo {phase.tournament.name}: {winners[0].name}', request.admin_id)
        else:
            if phase.name == 'Octavos de Final':
                next_phase_name = 'Cuartos de Final'
            elif phase.name == 'Cuartos de Final':
                next_phase_name = 'Semifinales'
            else:
                next_phase_name = 'Final'

            next_phase = Phase.objects.create(
                tournament=phase.tournament,
                name=next_phase_name,
                phase_order=phase.phase_order + 1,
            )

            mid = len(winners) // 2
            for i in range(mid):
                PhaseMatch.objects.create(
                    phase=next_phase,
                    team_1=winners[i],
                    team_2=winners[len(winners) - 1 - i],
                )

            create_log(f'Nueva fase generada: {next_phase_name} en torneo {phase.tournament.name}', request.admin_id)

    return JsonResponse({
        'id': match.id,
        'gf': match.gf,
        'gc': match.gc,
        'datematch': str(match.datematch) if match.datematch else None,
        'next_phase_generated': all_done and len(winners) > 1 if all_done else False,
    }, status=200)

@csrf_exempt
@require_POST
@admin_required
def delete_tournament(request, tournament_id):
    try:
        tournament = Tournament.objects.get(id=tournament_id)
    except Tournament.DoesNotExist:
        return JsonResponse({'error': 'Tournament not found'}, status=404)
    name = tournament.name
    tournament.delete()
    create_log(f'Torneo {name} fue eliminado', request.admin_id)
    return JsonResponse({'message': f'Tournament {name} deleted'}, status=200)


@csrf_exempt
@require_POST
@admin_required
def delete_team(request, team_id):
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        return JsonResponse({'error': 'Team not found'}, status=404)
    name = team.name
    tournament_name = team.tournament.name
    team.delete()
    create_log(f'Equipo {name} fue eliminado del torneo {tournament_name}', request.admin_id)
    return JsonResponse({'message': f'Team {name} deleted'}, status=200)


@csrf_exempt
@require_POST
@admin_required
def delete_participant(request, participant_id):
    try:
        participant = Participant.objects.get(id=participant_id)
    except Participant.DoesNotExist:
        return JsonResponse({'error': 'Participant not found'}, status=404)
    name = participant.name
    team_name = participant.team.name
    participant.delete()
    create_log(f'Participante {name} fue eliminado del equipo {team_name}', request.admin_id)
    return JsonResponse({'message': f'Participant {name} deleted'}, status=200)


@csrf_exempt
@require_POST
@admin_required
def delete_match(request, match_id):
    try:
        match = Match.objects.get(id=match_id)
    except Match.DoesNotExist:
        return JsonResponse({'error': 'Match not found'}, status=404)
    info = f'{match.team_1} vs {match.team_2}'
    tournament_name = match.tournament.name
    match.delete()
    create_log(f'Partido {info} fue eliminado del torneo {tournament_name}', request.admin_id)
    return JsonResponse({'message': f'Match {info} deleted'}, status=200)


@csrf_exempt
@require_POST
@admin_required
def delete_administrator(request, admin_id):
    try:
        admin = Administrator.objects.get(id=admin_id)
    except Administrator.DoesNotExist:
        return JsonResponse({'error': 'Administrator not found'}, status=404)
    if admin.id == request.admin_id:
        return JsonResponse({'error': 'Cannot delete yourself'}, status=400)
    name = admin.name
    admin.delete()
    create_log(f'Admin {name} fue eliminado', request.admin_id)
    return JsonResponse({'message': f'Administrator {name} deleted'}, status=200)