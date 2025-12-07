from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User

@receiver(pre_delete, sender=User)
def handle_user_deletion(sender, instance, **kwargs):
    """
    Preserve reviews when users are deleted
    """
    from .models import SellerRating
    
    # Handle seller deletions
    if hasattr(instance, 'profile') and instance.profile.is_seller:
        SellerRating.objects.filter(seller=instance.profile).update(
            seller=None,
            seller_was_deleted=True
        )
    
    # Handle reviewer deletions
    SellerRating.objects.filter(reviewer_user=instance).update(
        reviewer_user=None,
        reviewer_account_deleted=True,
        reviewer_name=f"Deleted User ({instance.email})"
    )