# Generated by Django 5.1.2 on 2024-11-25 06:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('node', '0005_post_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='author',
            name='page',
            field=models.TextField(blank=True, null=True),
        ),
    ]
