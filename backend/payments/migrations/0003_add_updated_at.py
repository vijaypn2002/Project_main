from django.db import migrations, models
import django.utils.timezone

class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0002_keep_history_0002"),
    ]

    operations = [
        # Add the column with a one-time default for existing rows
        migrations.AddField(
            model_name="payment",
            name="updated_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,  # set once, then rely on model's auto_now
        ),
    ]
