from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q
from apps.models import User, Company, Product, Category, Sale, SaleItem, SubscriptionStatus
from apps.signals import DEFAULT_CATEGORIES


class Command(BaseCommand):
    help = "Markazsiz kassirlar uchun shaxsiy kompaniyalar yaratish va mahsulotlarni, savdolarni ko'chirish (split_personal_data)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--assign',
            action='append',
            help='SKU va telefon raqamini bog\'lash, masalan: --assign SKU=phone (takrorlanishi mumkin)'
        )
        parser.add_argument(
            '--cashier-ids',
            type=str,
            help='Faqat ko\'rsatilgan kassir ID lari (vergul bilan ajratilgan, masalan: 18,19)'
        )
        parser.add_argument(
            '--apply',
            action='store_true',
            help='O\'zgarishlarni bazaga saqlash (default dry-run)'
        )

    def handle(self, *args, **options):
        apply_changes = options.get('apply', False)
        assign_raw = options.get('assign') or []
        cashier_ids_raw = options.get('cashier_ids')

        cashier_ids_filter = []
        if cashier_ids_raw:
            for cid in cashier_ids_raw.split(','):
                if cid.strip().isdigit():
                    cashier_ids_filter.append(int(cid.strip()))

        assign_map = {}
        for item in assign_raw:
            if '=' in item:
                k, v = item.split('=', 1)
                assign_map[k.strip()] = v.strip()

        markazless_cashiers = User.objects.filter(role='cashier', markaz__isnull=True)
        if cashier_ids_filter:
            markazless_cashiers = markazless_cashiers.filter(id__in=cashier_ids_filter)

        all_products = Product.objects.all()

        self.stdout.write(self.style.SUCCESS("=== DATABASE REPORT ==="))
        self.stdout.write(f"Markazsiz kassirlar soni (filtrlangan): {markazless_cashiers.count()}")
        for c in markazless_cashiers:
            self.stdout.write(f"  - ID: {c.id}, Tel: {c.phone_number}, Ism: {c.first_name} {c.last_name}, Company_id: {c.company_id}")

        self.stdout.write(f"\nBarcha mahsulotlar soni: {all_products.count()}")
        for p in all_products:
            self.stdout.write(f"  - SKU: {p.sku}, Nomi: {p.name}, Company_id: {p.company_id}")

        sale_items_count = SaleItem.objects.count()
        self.stdout.write(f"\nJami savdolar (Sale) soni: {Sale.objects.count()}, SaleItem soni: {sale_items_count}")

        phone_to_skus = {}
        for k, v in assign_map.items():
            if len(v) >= 9 and v.isdigit():
                phone_to_skus.setdefault(v, []).append(k)
            elif len(k) >= 9 and k.isdigit():
                phone_to_skus.setdefault(k, []).append(v)

        plans = []
        for cashier in markazless_cashiers:
            phone = cashier.phone_number
            assigned_skus = phone_to_skus.get(phone, [])

            target_products = []
            if cashier.company:
                target_products = list(Product.objects.filter(company=cashier.company, sku__in=assigned_skus))

            unmatched_skus = [sku for sku in assigned_skus if not any(p.sku == sku for p in target_products)]

            # Check cashier name matching for sales in cashier.company
            matching_sales = []
            if cashier.company:
                company_cashiers = list(User.objects.filter(company=cashier.company, role='cashier'))
                name_variants = {
                    (cashier.first_name or '').strip(),
                    f"{cashier.first_name or ''} {cashier.last_name or ''}".strip(),
                    (cashier.phone_number or '').strip()
                }
                name_variants = {v for v in name_variants if v}

                company_sales = Sale.objects.filter(company=cashier.company)
                for sale in company_sales:
                    if sale.cashier and sale.cashier.strip() in name_variants:
                        matching_cashiers = [
                            c for c in company_cashiers
                            if sale.cashier.strip() in {
                                (c.first_name or '').strip(),
                                f"{c.first_name or ''} {c.last_name or ''}".strip(),
                                (c.phone_number or '').strip()
                            }
                        ]
                        if len(matching_cashiers) > 1:
                            raise ValueError(
                                f"Diqqat: '{sale.cashier}' ismi bir nechta kassirga mos keladi (IDs: {[c.id for c in matching_cashiers]}). Savdo ID: {sale.id}. To'xtatildi."
                            )
                        matching_sales.append(sale)

            plans.append({
                "cashier": cashier,
                "target_products": target_products,
                "unmatched_skus": unmatched_skus,
                "matching_sales": matching_sales
            })

        self.stdout.write(self.style.SUCCESS(f"\n=== DRY-RUN PLAN ({'APPLY MODE' if apply_changes else 'DRY-RUN'}) ==="))
        for plan in plans:
            cashier = plan['cashier']
            target_products = plan['target_products']
            unmatched_skus = plan['unmatched_skus']
            matching_sales = plan['matching_sales']

            name_part = f"{cashier.first_name or ''} {cashier.last_name or ''}".strip()
            phone_part = (cashier.phone_number or '').strip()
            if name_part:
                comp_name = f"{name_part} {phone_part} (shaxsiy)" if phone_part else f"{name_part} (shaxsiy)"
            else:
                comp_name = f"{phone_part} (shaxsiy)" if phone_part else "Shaxsiy kompaniya"

            self.stdout.write(f"\nKassir ID {cashier.id} ({phone_part} - {name_part}):")
            self.stdout.write(f"  -> Yangi shaxsiy kompaniya: '{comp_name}' (subscription_status=active, expires_at=None)")
            self.stdout.write(f"  -> Ko'chiriladigan mahsulotlar ({len(target_products)} ta):")
            for p in target_products:
                cat = p.category
                # check if category already exists in new company or will be created
                cat_exists = Category.objects.filter(company__name=comp_name, key=cat.key).exists() if cat else False
                cat_status = "mavjud" if cat_exists else "yaratiladi"
                self.stdout.write(f"     * SKU: {p.sku}, Nomi: {p.name}, Kategoriya: key='{cat.key if cat else None}', label='{cat.label if cat else None}' ({cat_status})")

            if unmatched_skus:
                self.stdout.write(self.style.WARNING(f"  -> Topilmagan/ko'chirilmaydigan SKU lar: {unmatched_skus}"))

            self.stdout.write(f"  -> Bog'langan savdolar ({len(matching_sales)} ta):")
            for s in matching_sales:
                self.stdout.write(f"     * Sale ID: {s.id}, Cashier matni: '{s.cashier}', Total: {s.total}, Item soni: {s.items.count()} (Sabab: Sale.cashier kassir ismiga/telefoniga mos)")

        if not apply_changes:
            self.stdout.write(self.style.SUCCESS("\nDry-run yakunlandi. Hech qanday o'zgarish yozilmadi. Qo'llash uchun --apply bayrog'ini qo'shing."))
            return

        # Apply changes
        with transaction.atomic():
            for plan in plans:
                cashier = plan['cashier']
                target_products = plan['target_products']
                matching_sales = plan['matching_sales']

                name_part = f"{cashier.first_name or ''} {cashier.last_name or ''}".strip()
                phone_part = (cashier.phone_number or '').strip()
                if name_part:
                    comp_name = f"{name_part} {phone_part} (shaxsiy)" if phone_part else f"{name_part} (shaxsiy)"
                else:
                    comp_name = f"{phone_part} (shaxsiy)" if phone_part else "Shaxsiy kompaniya"

                new_company = Company.objects.create(
                    name=comp_name,
                    subscription_status=SubscriptionStatus.ACTIVE,
                    subscription_expires_at=None,
                )

                # Create default categories and copy product categories
                for cat_def in DEFAULT_CATEGORIES:
                    Category.objects.get_or_create(company=new_company, key=cat_def["key"], defaults=cat_def)

                # Assign company & managed_by to cashier
                cashier.company = new_company
                if not cashier.managed_by:
                    superadmin = User.objects.filter(role='superadmin', company_id=plan['cashier'].company_id).first()
                    cashier.managed_by = superadmin
                cashier.save(update_fields=['company', 'managed_by'])

                # Move products and their categories ensuring product.category.company == product.company
                for prod in target_products:
                    old_cat = prod.category
                    new_cat = None
                    if old_cat:
                        new_cat, _ = Category.objects.get_or_create(
                            company=new_company,
                            key=old_cat.key,
                            defaults={
                                "label": old_cat.label,
                                "icon": old_cat.icon,
                                "accent": old_cat.accent
                            }
                        )
                    prod.company = new_company
                    prod.category = new_cat
                    prod.save(update_fields=['company', 'category'])

                # Move matching sales (Sale.company = new_company), keeping SaleItem.product intact
                for sale in matching_sales:
                    sale.company = new_company
                    sale.save(update_fields=['company'])

        self.stdout.write(self.style.SUCCESS("\nBarcha ma'lumotlar, mahsulotlar, kategoriyalar va savdolar muvaffaqiyatli ko'chirildi!"))
