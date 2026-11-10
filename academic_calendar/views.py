from datetime import date

from django.http import HttpResponseForbidden
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AcademicCalendarEventForm
from .models import AcademicCalendarEvent
from attendance.services import flag_holiday_conflicts


def can_manage_calendar(user):
    return (
        user.is_authenticated
        and hasattr(user, "profile")
        and user.profile.role == "vice_principal"
    )

def require_calendar_manager(user):
    if not can_manage_calendar(user):
        raise PermissionDenied(
            "Only the Vice Principal can manage calendar events."
        )


@login_required
def calendar_view(request):
    events = AcademicCalendarEvent.objects.select_related(
        "class_section",
        "created_by",
    )

    if not can_manage_calendar(request.user):
        events = events.filter(status="published")

    search = request.GET.get("q", "").strip()
    event_type = request.GET.get("event_type", "").strip()
    academic_year = request.GET.get("academic_year", "").strip()
    selected_month = request.GET.get("month", "").strip()

    if search:
        events = events.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
        )

    if event_type:
        events = events.filter(event_type=event_type)

    if academic_year:
        events = events.filter(academic_year=academic_year)

    if selected_month:
        try:
            year_text, month_text = selected_month.split("-")
            year_number = int(year_text)
            month_number = int(month_text)

            if not 1 <= month_number <= 12:
                raise ValueError

            month_start = date(year_number, month_number, 1)

            if month_number == 12:
                month_end = date(year_number + 1, 1, 1)
            else:
                month_end = date(year_number, month_number + 1, 1)

            events = events.filter(
                start_date__lt=month_end,
                end_date__gte=month_start,
            )

        except (ValueError, TypeError):
            messages.warning(
                request,
                "Invalid month filter was ignored.",
            )

    academic_years = (
        AcademicCalendarEvent.objects.order_by()
        .values_list("academic_year", flat=True)
        .distinct()
    )

    return render(
        request,
        "academic_calendar/calendar.html",
        {
            "events": events,
            "can_edit": can_manage_calendar(request.user),
            "event_types": AcademicCalendarEvent.EVENT_TYPES,
            "academic_years": academic_years,
            "search": search,
            "selected_type": event_type,
            "selected_year": academic_year,
            "selected_month": selected_month,
        },
    )


@login_required
def event_add(request):
    require_calendar_manager(request.user)

    if request.method == "POST":
        form = AcademicCalendarEventForm(request.POST)

        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user

            try:
                with transaction.atomic():
                    event.full_clean()
                    event.save()
                    flag_holiday_conflicts(event)
            except Exception as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(
                    request,
                    "Calendar event created successfully.",
                )
                return redirect("academic_calendar:calendar")
    else:
        form = AcademicCalendarEventForm()

    return render(
        request,
        "academic_calendar/event_form.html",
        {
            "form": form,
            "page_title": "Add Calendar Event",
            "button_text": "Create Event",
        },
    )


@login_required
def event_detail(request, pk):
    event = get_object_or_404(
        AcademicCalendarEvent.objects.select_related(
            "class_section",
            "created_by",
        ),
        pk=pk,
    )

    if (
        event.status != "published"
        and not can_manage_calendar(request.user)
    ):
        raise PermissionDenied

    return render(
        request,
        "academic_calendar/event_detail.html",
        {
            "event": event,
            "can_edit": can_manage_calendar(request.user),
        },
    )


@login_required
def event_edit(request, pk):
    require_calendar_manager(request.user)

    event = get_object_or_404(
        AcademicCalendarEvent,
        pk=pk,
    )

    if request.method == "POST":
        form = AcademicCalendarEventForm(
            request.POST,
            instance=event,
        )

        if form.is_valid():
            updated_event = form.save(commit=False)

            try:
                with transaction.atomic():
                    updated_event.full_clean()
                    updated_event.save()
                    flag_holiday_conflicts(updated_event)
            except Exception as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(
                    request,
                    "Calendar event updated successfully.",
                )
                return redirect(
                    "academic_calendar:event_detail",
                    pk=event.pk,
                )
    else:
        form = AcademicCalendarEventForm(instance=event)

    return render(
        request,
        "academic_calendar/event_form.html",
        {
            "form": form,
            "page_title": "Edit Calendar Event",
            "button_text": "Save Changes",
        },
    )


@login_required
def event_delete(request, pk):
    require_calendar_manager(request.user)

    event = get_object_or_404(
        AcademicCalendarEvent,
        pk=pk,
    )

    if request.method == "POST":
        event.delete()

        messages.success(
            request,
            "Calendar event deleted successfully.",
        )

        return redirect("academic_calendar:calendar")

    return render(
        request,
        "academic_calendar/event_confirm_delete.html",
        {
            "event": event,
        },
    )