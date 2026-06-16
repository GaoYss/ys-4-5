from decimal import Decimal

from django.db.models import Count, Exists, F, OuterRef, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import Bill, Building, FeeType, Payment, Reminder, Room
from .serializers import (
    BillSerializer,
    BuildingDetailSerializer,
    BuildingSerializer,
    FeeTypeSerializer,
    PaymentSerializer,
    ReminderSerializer,
    RoomSerializer,
)
from .services import create_overdue_reminders, dashboard_stats, generate_bills, pay_bill

HIGH_DEBT_THRESHOLD = Decimal("500.00")


def _annotate_room_debt(queryset):
    today = timezone.localdate()
    unpaid_bills = Bill.objects.filter(
        room=OuterRef("pk"),
        status__in=[Bill.UNPAID, Bill.OVERDUE],
    )
    overdue_bills = Bill.objects.filter(
        room=OuterRef("pk"),
        status__in=[Bill.UNPAID, Bill.OVERDUE],
        due_date__lt=today,
    )
    return queryset.annotate(
        unpaid_amount=Coalesce(Sum("bills__amount", filter=Q(bills__status__in=[Bill.UNPAID, Bill.OVERDUE])), Value(Decimal("0.00"))),
        overdue_amount=Coalesce(
            Sum(
                "bills__amount",
                filter=Q(bills__status__in=[Bill.UNPAID, Bill.OVERDUE]) & Q(bills__due_date__lt=today),
            ),
            Value(Decimal("0.00")),
        ),
        has_unpaid=Exists(unpaid_bills),
        has_overdue=Exists(overdue_bills),
    )


class BuildingViewSet(viewsets.ModelViewSet):
    serializer_class = BuildingSerializer
    queryset = Building.objects.all()

    def get_queryset(self):
        debt_status = self.request.query_params.get("debt_status")
        high_debt_threshold = Decimal(self.request.query_params.get("high_debt_threshold", HIGH_DEBT_THRESHOLD))
        today = timezone.localdate()

        queryset = Building.objects.all()

        unpaid_bill_filter = Q(rooms__bills__status__in=[Bill.UNPAID, Bill.OVERDUE])
        overdue_bill_filter = Q(rooms__bills__status__in=[Bill.UNPAID, Bill.OVERDUE]) & Q(
            rooms__bills__due_date__lt=today
        )

        queryset = queryset.annotate(
            room_count=Count("rooms", distinct=True),
            unpaid_room_count=Count("rooms", filter=unpaid_bill_filter, distinct=True),
            overdue_room_count=Count("rooms", filter=overdue_bill_filter, distinct=True),
            total_unpaid_amount=Coalesce(
                Sum("rooms__bills__amount", filter=Q(rooms__bills__status__in=[Bill.UNPAID, Bill.OVERDUE])),
                Value(Decimal("0.00")),
            ),
        )

        queryset = queryset.annotate(
            high_debt_room_count=Count(
                "rooms",
                filter=Q(
                    rooms__pk__in=Room.objects.annotate(
                        room_unpaid=Coalesce(
                            Sum(
                                "bills__amount",
                                filter=Q(bills__status__in=[Bill.UNPAID, Bill.OVERDUE]),
                            ),
                            Value(Decimal("0.00")),
                        )
                    )
                    .filter(room_unpaid__gte=high_debt_threshold)
                    .values("pk")
                ),
                distinct=True,
            )
        )

        if debt_status == "unpaid":
            queryset = queryset.filter(unpaid_room_count__gt=0)
        elif debt_status == "overdue":
            queryset = queryset.filter(overdue_room_count__gt=0)
        elif debt_status == "high_debt":
            queryset = queryset.filter(high_debt_room_count__gt=0)

        return queryset.order_by("name")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return BuildingDetailSerializer
        return BuildingSerializer


class RoomViewSet(viewsets.ModelViewSet):
    serializer_class = RoomSerializer
    queryset = Room.objects.all()

    def get_queryset(self):
        queryset = Room.objects.select_related("building").all()
        queryset = _annotate_room_debt(queryset)

        building = self.request.query_params.get("building")
        if building:
            queryset = queryset.filter(building_id=building)

        debt_status = self.request.query_params.get("debt_status")
        high_debt_threshold = Decimal(self.request.query_params.get("high_debt_threshold", HIGH_DEBT_THRESHOLD))

        if debt_status == "unpaid":
            queryset = queryset.filter(has_unpaid=True)
        elif debt_status == "overdue":
            queryset = queryset.filter(has_overdue=True)
        elif debt_status == "high_debt":
            queryset = queryset.filter(unpaid_amount__gte=high_debt_threshold)

        return queryset


class FeeTypeViewSet(viewsets.ModelViewSet):
    queryset = FeeType.objects.all()
    serializer_class = FeeTypeSerializer


class BillViewSet(viewsets.ModelViewSet):
    queryset = Bill.objects.select_related("room", "room__building", "fee_type").all()
    serializer_class = BillSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        period = self.request.query_params.get("period")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if period:
            queryset = queryset.filter(period=period)
        return queryset

    @action(detail=False, methods=["post"])
    def generate(self, request):
        fee_type_id = request.data.get("fee_type")
        period = request.data.get("period")
        due_date = request.data.get("due_date")
        room_ids = request.data.get("room_ids")
        if not all([fee_type_id, period, due_date]):
            return Response({"detail": "fee_type、period、due_date 为必填项"}, status=status.HTTP_400_BAD_REQUEST)

        created, skipped = generate_bills(fee_type_id, period, due_date, room_ids)
        return Response(
            {
                "created": BillSerializer(created, many=True).data,
                "created_count": len(created),
                "skipped_count": skipped,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        bill = self.get_object()
        try:
            payment = pay_bill(bill, request.data.get("method", Payment.WECHAT), request.data.get("payer", ""))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("bill", "bill__room", "bill__room__building", "bill__fee_type").all()
    serializer_class = PaymentSerializer

    def create(self, request, *args, **kwargs):
        bill = get_object_or_404(Bill.objects.select_related("room"), pk=request.data.get("bill"))
        try:
            payment = pay_bill(bill, request.data.get("method", Payment.WECHAT), request.data.get("payer", ""))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(payment).data, status=status.HTTP_201_CREATED)


class ReminderViewSet(viewsets.ModelViewSet):
    queryset = Reminder.objects.select_related("bill", "bill__room", "bill__room__building", "bill__fee_type").all()
    serializer_class = ReminderSerializer

    @action(detail=False, methods=["post"])
    def create_overdue(self, request):
        reminders = create_overdue_reminders(request.data.get("channel", Reminder.SMS))
        return Response(
            {"created_count": len(reminders), "created": ReminderSerializer(reminders, many=True).data},
            status=status.HTTP_201_CREATED,
        )


@api_view(["GET"])
def dashboard(request):
    stats = dashboard_stats()
    recent = BillSerializer(stats.pop("recent_bills"), many=True).data
    return Response({**stats, "recent_bills": recent})
