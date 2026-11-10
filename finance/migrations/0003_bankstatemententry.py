# Generated for finance reconciliation workflow.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import django.core.validators
from decimal import Decimal


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0002_feestructure_studentfee_fee_structure_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BankStatementEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("statement_date", models.DateField()),
                ("bank_reference", models.CharField(db_index=True, max_length=100)),
                ("description", models.CharField(blank=True, max_length=250)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))])),
                ("status", models.CharField(choices=[("unmatched", "Unmatched"), ("matched", "Matched")], db_index=True, default="unmatched", max_length=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_bank_statement_entries", to=settings.AUTH_USER_MODEL)),
                ("matched_payment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="bank_statement_matches", to="finance.feepayment")),
            ],
            options={"ordering": ["-statement_date", "-created_at"]},
        ),
    ]
