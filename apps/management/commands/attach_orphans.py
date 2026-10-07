from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.models import User, Markaz, Company
from apps.serializers.users import normalize_phone


class Command(BaseCommand):
    help = "Attach orphan users and markazs with company_id=None to a specified company."

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            required=False,
            help='Target company ID to attach orphan records to.'
        )
        parser.add_argument(
            '--all-orphan-cashiers',
            action='store_true',
            help='Attach all cashiers where company_id is NULL.'
        )
        parser.add_argument(
            '--include-superadmin',
            type=str,
            help='Phone number of superadmin to attach if company_id is NULL.'
        )
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Apply changes (default is dry-run).'
        )

    def handle(self, *args, **options):
        company_id = options.get('company_id')
        if company_id is None:
            raise CommandError("--company-id parametri kiritilishi shart.")

        try:
            company = Company.objects.get(pk=company_id)
        except Company.DoesNotExist:
            raise CommandError(f"Kompaniya (ID: {company_id}) topilmadi.")

        all_orphans = options['all_orphan_cashiers']
        superadmin_phone = options['include_superadmin']
        apply_changes = options['apply']

        users_to_attach = []
        if all_orphans:
            cashiers = User.objects.filter(company__isnull=True, role='cashier')
            users_to_attach.extend(cashiers)

        if superadmin_phone:
            normalized_phone = normalize_phone(superadmin_phone)
            try:
                superadmin = User.objects.get(phone_number=normalized_phone, company__isnull=True, role='superadmin')
                users_to_attach.append(superadmin)
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Superadmin ({superadmin_phone}) company=None bilan topilmadi."))

        markazs_to_attach = list(Markaz.objects.filter(company__isnull=True))

        for user in users_to_attach:
            if user.markaz and user.markaz.company and user.markaz.company != company:
                raise CommandError(f"Kassir {user.phone_number} ning markazi ({user.markaz.name}) boshqa kompaniyaga ({user.markaz.company.name}) tegishli!")

        self.stdout.write("--- DRY RUN / ATTACH REPORT ---")
        self.stdout.write(f"Target Company: {company.name} (ID: {company.id})")
        self.stdout.write(f"Users to attach ({len(users_to_attach)}):")
        for u in users_to_attach:
            self.stdout.write(f"  - User ID: {u.id}, Phone: {u.phone_number}, Role: {u.role}")

        self.stdout.write(f"Markazs to attach ({len(markazs_to_attach)}):")
        for m in markazs_to_attach:
            self.stdout.write(f"  - Markaz ID: {m.id}, Name: {m.name}")

        if not apply_changes:
            self.stdout.write(self.style.WARNING("DRY-RUN mode. No changes were written to the database. Use --apply to execute."))
            return

        with transaction.atomic():
            for user in users_to_attach:
                user.company = company
                user.save(update_fields=['company'])

            for markaz in markazs_to_attach:
                markaz.company = company
                markaz.save(update_fields=['company'])

        self.stdout.write(self.style.SUCCESS(f"Successfully attached {len(users_to_attach)} users and {len(markazs_to_attach)} markazs to company {company.name}."))
