"""
Contact business logic services
"""
import logging
import csv
import io
from django.db import transaction
from django.db.models import F
from django.core.exceptions import ValidationError
from typing import Dict, List, Optional
import phonenumbers

from core.exceptions import (
    InvalidContactError,
    DuplicateContactError,
    ContactNotFoundError
)
from apps.contacts.models import Contact, ContactList

logger = logging.getLogger(__name__)


class ContactService:
    """Service for contact business logic"""
    
    @staticmethod
    @transaction.atomic
    def create_contact(
        contact_list_id: int,
        phone: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Create a new contact with validation
        
        Args:
            contact_list_id: Contact list ID
            phone: Phone number
            first_name: First name
            last_name: Last name
            email: Email address
            **kwargs: Additional contact fields
            
        Returns:
            dict: Created contact info
            
        Raises:
            InvalidContactError: If contact data is invalid
            DuplicateContactError: If contact already exists
        """
        # Validate phone number
        try:
            parsed = phonenumbers.parse(phone, "US")
            if not phonenumbers.is_valid_number(parsed):
                raise InvalidContactError(f"Invalid phone number: {phone}")
            phone = phonenumbers.format_number(
                parsed,
                phonenumbers.PhoneNumberFormat.E164
            )
        except phonenumbers.NumberParseException as e:
            raise InvalidContactError(f"Invalid phone number format: {phone}")
        
        # Check for duplicates
        if Contact.objects.filter(
            contact_list_id=contact_list_id,
            phone=phone
        ).exists():
            raise DuplicateContactError(
                f"Contact with phone {phone} already exists in this list"
            )
        
        # Create contact
        contact = Contact.objects.create(
            contact_list_id=contact_list_id,
            phone=phone,
            first_name=first_name or '',
            last_name=last_name or '',
            email=email or '',
            **kwargs
        )
        
        # Update contact list count
        contact_list = contact.contact_list
        contact_list.total_contacts += 1
        contact_list.save(update_fields=['total_contacts'])
        
        logger.info(
            "Contact created",
            extra={
                'contact_id': contact.id,
                'contact_list_id': contact_list_id,
                'phone': phone
            }
        )
        
        return {
            'success': True,
            'contact_id': contact.id,
            'phone': contact.phone,
            'name': f"{contact.first_name} {contact.last_name}".strip()
        }
    
    @staticmethod
    @transaction.atomic
    def import_contacts_from_csv(
        contact_list_id: int,
        csv_file,
        user,
        skip_duplicates: bool = True
    ) -> Dict:
        """
        Import contacts from CSV file using bulk_create for performance.
        Processes thousands of rows with a single DB insert instead of N queries.
        """
        try:
            contact_list = ContactList.objects.get(id=contact_list_id)
        except ContactList.DoesNotExist:
            raise InvalidContactError(f"Contact list {contact_list_id} not found")

        csv_content = csv_file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_content))

        # Pre-load existing phones for this list in one query → O(1) lookups
        if skip_duplicates:
            existing_phones: set = set(
                Contact.objects.filter(contact_list=contact_list)
                .values_list('phone', flat=True)
            )
        else:
            existing_phones = set()

        to_create: List[Contact] = []
        skipped = 0
        errors = []
        BATCH_SIZE = 1000

        for row_num, row in enumerate(csv_reader, start=2):
            phone = row.get('phone', '').strip()
            if not phone:
                skipped += 1
                errors.append(f"Row {row_num}: Missing phone number")
                continue

            # Normalize phone
            try:
                parsed = phonenumbers.parse(phone, 'CO')
                if not phonenumbers.is_valid_number(parsed):
                    raise ValueError('Invalid number')
                phone = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            except Exception:
                skipped += 1
                errors.append(f"Row {row_num}: Invalid phone '{phone}'")
                continue

            if phone in existing_phones:
                skipped += 1
                continue

            existing_phones.add(phone)  # Avoid dupes within the same file
            to_create.append(Contact(
                contact_list=contact_list,
                phone=phone,
                first_name=row.get('first_name', '').strip(),
                last_name=row.get('last_name', '').strip(),
                email=row.get('email', '').strip() or None,
                company=row.get('company', '').strip(),
                address=row.get('address', '').strip(),
                city=row.get('city', '').strip(),
                state=row.get('state', '').strip(),
                zip_code=row.get('zip_code', '').strip(),
                country=row.get('country', 'CO').strip(),
            ))

        # Bulk insert in batches — single transaction, minimal round-trips
        imported = 0
        for i in range(0, len(to_create), BATCH_SIZE):
            batch = to_create[i:i + BATCH_SIZE]
            created = Contact.objects.bulk_create(batch, ignore_conflicts=True, batch_size=BATCH_SIZE)
            imported += len(created)

        # Update list counter in one atomic expression
        if imported:
            ContactList.objects.filter(pk=contact_list_id).update(
                total_contacts=F('total_contacts') + imported
            )

        logger.info(
            "Contacts imported from CSV",
            extra={'contact_list_id': contact_list_id, 'imported': imported, 'skipped': skipped, 'user_id': user.id}
        )

        return {
            'success': True,
            'imported': imported,
            'skipped': skipped,
            'errors': errors[:10],
            'total_errors': len(errors),
        }
    
    @staticmethod
    @transaction.atomic
    def update_contact_status(
        contact_id: int,
        status: str,
        notes: Optional[str] = None
    ) -> Dict:
        """
        Update contact status
        
        Args:
            contact_id: Contact ID
            status: New status
            notes: Optional notes
            
        Returns:
            dict: Updated contact info
        """
        try:
            contact = Contact.objects.get(id=contact_id)
        except Contact.DoesNotExist:
            raise ContactNotFoundError(f"Contact {contact_id} not found")
        
        old_status = contact.status
        contact.status = status
        
        if notes:
            contact.notes.create(content=notes)
        
        contact.save()
        
        logger.info(
            "Contact status updated",
            extra={
                'contact_id': contact_id,
                'old_status': old_status,
                'new_status': status
            }
        )
        
        return {
            'success': True,
            'contact_id': contact.id,
            'old_status': old_status,
            'new_status': status
        }
    
    @staticmethod
    def get_contact_statistics(contact_list_id: int) -> Dict:
        """
        Get contact list statistics
        
        Args:
            contact_list_id: Contact list ID
            
        Returns:
            dict: Contact list statistics
        """
        try:
            contact_list = ContactList.objects.get(id=contact_list_id)
        except ContactList.DoesNotExist:
            raise InvalidContactError(f"Contact list {contact_list_id} not found")
        
        contacts = Contact.objects.filter(contact_list=contact_list)
        
        # Count by status
        status_counts = {}
        for status_code, status_name in Contact.STATUS_CHOICES:
            count = contacts.filter(status=status_code).count()
            status_counts[status_code] = {
                'name': status_name,
                'count': count
            }
        
        # Count by priority
        priority_counts = {}
        for priority in range(11):  # 0-10
            count = contacts.filter(priority=priority).count()
            if count > 0:
                priority_counts[priority] = count
        
        stats = {
            'contact_list_id': contact_list.id,
            'contact_list_name': contact_list.name,
            'total_contacts': contacts.count(),
            'status_breakdown': status_counts,
            'priority_breakdown': priority_counts,
            'has_email': contacts.exclude(email='').count(),
            'has_company': contacts.exclude(company='').count()
        }
        
        return stats
    
    @staticmethod
    @transaction.atomic
    def bulk_update_status(
        contact_ids: List[int],
        status: str,
        user
    ) -> Dict:
        """
        Bulk update contact statuses
        """
        updated = Contact.objects.filter(
            id__in=contact_ids
        ).update(status=status)

        logger.info(
            "Bulk contact status update",
            extra={'updated_count': updated, 'new_status': status, 'user_id': user.id}
        )
        return {'success': True, 'updated': updated}

    @staticmethod
    @transaction.atomic
    def import_contacts_from_excel(
        contact_list_id: int,
        excel_file,
        user,
        skip_duplicates: bool = True,
    ) -> Dict:
        """
        Importar contactos desde archivo Excel (.xlsx / .xls).
        Requiere openpyxl (ya incluido en django).
        Reutiliza la misma lógica de CSV convirtiéndolo en un DictReader virtual.
        """
        try:
            import openpyxl
        except ImportError:
            raise InvalidContactError("openpyxl no está instalado. Ejecuta: pip install openpyxl")

        wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
        ws = wb.active

        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return {'success': True, 'imported': 0, 'skipped': 0, 'errors': [], 'total_errors': 0}

        # Primera fila como cabecera
        headers = [str(h).strip().lower() if h else '' for h in rows[0]]

        import io
        output = io.StringIO()
        import csv as csv_mod
        writer = csv_mod.writer(output)
        writer.writerow(headers)
        for row in rows[1:]:
            writer.writerow(['' if v is None else str(v) for v in row])

        output.seek(0)

        class FakeFile:
            def read(self):
                return output.getvalue().encode('utf-8')

        return ContactService.import_contacts_from_csv(
            contact_list_id=contact_list_id,
            csv_file=FakeFile(),
            user=user,
            skip_duplicates=skip_duplicates,
        )
