# Generated by Django 4.2.5 on 2023-10-05 18:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workshop', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workrequest',
            name='department',
            field=models.CharField(blank=True, choices=[('', ''), ('AUTO', 'Automotive'), ('ELEC', 'Electrical'), ('HR', 'HR'), ('MAINT', 'Maintenance'), ('RND', 'RnD'), ('UTL', 'Utility')], max_length=50),
        ),
    ]
