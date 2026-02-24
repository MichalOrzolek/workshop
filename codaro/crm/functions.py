from .models import RescueTeam, Report


def rescue_status(report):
    if report and isinstance(report, Report) and report.rescue_team:
        rescue_availabilty = True if report.report_status in ['Success', 'Failed', 'Cancelled'] else False
        RescueTeam.objects.filter(id=report.rescue_team.id).update(availability=rescue_availabilty)
        if report.closed_at:
            Report.objects.filter(id=report.id).update(
                seconds_rescue_team_assigned=(report.rescue_assigned_at - report.created_at).total_seconds(),
                seconds_closed_from_assign=(report.closed_at - report.rescue_assigned_at).total_seconds(),
                seconds_closed_from_report=(report.closed_at - report.created_at).total_seconds(),
            )
        else:
            Report.objects.filter(id=report.id).update(
                seconds_rescue_team_assigned=(report.rescue_assigned_at - report.created_at).total_seconds(),
            )

def display_seconds(seconds):
    if seconds:
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{hours}H:{minutes:02d}M:{sec:02d}S"
        elif minutes > 0:
            return f"{minutes}M:{sec:02d}S"
        else:
            return f"{sec}S"
    return '-'
