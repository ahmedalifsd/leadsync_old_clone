# Manual Payment Processing Guide

## Overview
LeadSync uses a manual payment verification system where customers submit payment requests with their contact details, and super admins approve payments by uploading transaction proof images.

---

## Payment Flow

### User (Owner) Side
1. User navigates to **My Plan** page
2. Clicks "Pay / Request" button on any plan
3. Modal opens collecting contact information:
   - Name (pre-filled with full name or username)
   - Phone number
   - Email (pre-filled with account email)
   - Optional contact note (e.g., payment method details)
4. User submits the payment request
5. System notifies all super admins of the new request
6. User sees "Pending Review" status in payment history until approved

### Super Admin Side
1. Super admin navigates to **Manage Plans** page
2. Sees "Manual Payment Requests" section with pending requests
3. Reviews customer details and payment information
4. For each request, admin can:
   - **Approve**: Upload transaction proof image, optionally override:
     - Plan selection
     - Billing cycle (monthly/yearly)
     - Payment method
     - Transaction ID
     - Admin notes
     - Auto-renew setting
   - **Reject**: Provide rejection reason (customer receives email explanation)
5. On approval, subscription is immediately activated
6. Customer receives activation email with plan details

---

## Image Storage & Backup

### Storage Location
**Payment proof images are stored in:**
```
media/payments/proofs/
```

### File Structure on Disk
```
LeadSync/
├── media/
│   ├── payments/
│   │   └── proofs/
│   │       ├── payment_1_image1.jpg
│   │       ├── payment_5_image2.png
│   │       └── ... (all transaction proof images)
```

### Image Handling
- Images uploaded by super admins during approval are automatically saved
- Field name in database: `Payment.payment_proof` (ImageField)
- Maximum file size: Limited by Django's `FILE_UPLOAD_MAX_MEMORY_SIZE` (default 2.5MB)
- Supported formats: All image types (JPG, PNG, GIF, etc.)

### Backup Recommendations
1. **Regular Backups**: Ensure `media/payments/proofs/` is included in backup strategy
2. **Cloud Storage**: Consider offloading proofs to AWS S3, Google Cloud Storage, or Azure Blob Storage
3. **Retention Policy**: Define how long proof images should be retained (compliance requirement)
4. **Access Control**: Ensure only authorized staff can access proof directory

---

## Database Fields

### Payment Model Extensions
The `Payment` model includes the following manual payment fields:

| Field | Type | Purpose |
|-------|------|---------|
| `payer_name` | CharField(150) | Customer name from payment request |
| `payer_phone` | CharField(50) | Customer phone for coordination |
| `payer_email` | EmailField | Customer email for notifications |
| `contact_note` | TextField | Optional customer note (e.g., payment method) |
| `payment_proof` | ImageField | Transaction screenshot (uploaded by admin) |
| `reviewed_at` | DateTimeField | Timestamp of approval |
| `reviewed_by` | ForeignKey(User) | Super admin who approved |
| `is_renewal` | BooleanField | Flags renewal vs fresh activation |
| `is_rejected` | BooleanField | Indicates rejection status |
| `rejected_at` | DateTimeField | Timestamp of rejection |
| `rejected_by` | ForeignKey(User) | Super admin who rejected |
| `rejection_reason` | TextField | Reason provided to customer |

---

## Duplicate Request Handling

### Problem
Users might accidentally submit multiple payment requests for the same subscription.

### Solution
- **Automatic Superseding**: When a user submits a NEW payment request for the same subscription, any previous PENDING requests are automatically marked as rejected
- **Reason**: "Superseded by newer payment request"
- **Effect**: Only the latest request appears in admin queue; older requests are archived in payment history

### User Experience
- User sees only the latest request in their payment history
- Previous requests show "Rejected (Superseded)" status
- Admin only reviews/approves the most recent request

---

## Rejection & Retry

### When Admin Rejects Payment
1. Admin clicks **Reject** button on payment request
2. Modal opens asking for rejection reason (required field)
3. Rejection reason is visible to customer (sent via email)
4. Payment remains in history marked as "Rejected"
5. Customer can submit a **new** payment request anytime

### Common Rejection Reasons
- "Transaction amount does not match requested plan price"
- "Proof image is unclear or incomplete"
- "No matching transaction found in our records"
- "Please verify payment method before resubmitting"

---

## Renewal Requests

### How Renewal Works
1. When subscription is expiring (≤7 days), a renewal alert appears on My Plan
2. User clicks "Request Renewal" button
3. Modal pre-fills with current plan details and [Renewal] tag
4. Admin approves renewal, subscription period extends from current end_date
5. **Important**: Renewal period starts the day AFTER current subscription ends (no overlap)

### Subscription Period Calculation
- **New Activation**: start_date = today, end_date = start_date + period (30/365 days)
- **Renewal**: start_date = old_end_date + 1 day, end_date = start_date + period

---

## Email Notifications

### Payment Submitted
- **Recipient**: All super admins
- **Subject**: "Manual Payment Request: [username] - [plan name]"
- **Contains**: Customer info, plan details, contact info

### Payment Approved
- **Recipient**: Customer/User
- **Subject**: "LeadSync - [Plan Name] Activated"
- **Contains**: Plan details, billing cycle, employee/lead limits, dashboard link

### Payment Rejected
- **Recipient**: Customer/User
- **Subject**: "LeadSync - Payment Request Rejected"
- **Contains**: Plan details, rejection reason, instructions for resubmission, support contact

---

## Admin Dashboard Columns

### Manual Payment Requests Table Displays:
| Column | Shows |
|--------|-------|
| Customer | Username + Email |
| Requested Plan | Plan name and billing cycle + renewal indicator |
| Amount | Final amount after discounts |
| Contact | Name, phone, email, and any note |
| Requested On | Submission date + due date |
| Approve/Reject | Inline form with file upload + action buttons |

---

## Django Settings Configuration

### Required Settings
```python
# LeadSync/settings.py

# Payment proof upload directory
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# File upload size limit
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5MB

# Support contacts (optional, shown to users)
SUPPORT_EMAIL = config('SUPPORT_EMAIL', default='support@leadsync.com')
SUPPORT_PHONE = config('SUPPORT_PHONE', default='')
SUPPORT_WHATSAPP = config('SUPPORT_WHATSAPP', default='')
```

### .env File
```
SUPPORT_EMAIL=support@leadsync.com
SUPPORT_PHONE=+92-300-XXXX
SUPPORT_WHATSAPP=+92-300-XXXX
```

---

## Troubleshooting

### Images Not Showing in Admin
**Problem**: Proof images don't appear in approve form
**Solution**: 
- Ensure `MEDIA_URL` and `MEDIA_ROOT` are configured
- Run `python manage.py collectstatic` if deploying
- Check file permissions on `media/payments/proofs/` directory

### Duplicate Requests Still Appearing
**Problem**: User sees multiple pending requests after submitting new one
**Solution**:
- Migration 0012 must be applied (`python manage.py migrate billing`)
- Restart Django application
- Check database field `is_rejected` for older requests

### Emails Not Sending
**Problem**: Customers/admins not receiving notifications
**Solution**:
- Verify `SUPPORT_EMAIL` in settings
- Check email backend configuration
- Review Django log files for email transmission errors

---

## Security Considerations

1. **File Validation**: Only image files accepted via `accept="image/*"` on upload form
2. **Access Control**: Only super admins can approve payment requests and view all proofs
3. **Audit Trail**: All approvals/rejections tracked via `reviewed_by`, `rejected_by` fields
4. **Customer Privacy**: Contact details only visible to super admins in approval view

---

## Future Enhancements

- [ ] Proof image validation (size/format) on frontend before upload
- [ ] Bulk approval feature for similar requests
- [ ] Admin dashboard with approval statistics and filtering
- [ ] Automated renewal reminder emails (7 days before expiry)
- [ ] Receipt/invoice generation for approved payments
- [ ] Integration with payment gateways for proof verification
- [ ] OCR for automatic transaction verification

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-18 | Initial manual payment system with rejection support and duplicate handling |

---

**For questions or issues, contact the development team.**
