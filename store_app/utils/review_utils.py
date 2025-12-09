# utils/review_utils.py
from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from ..models import SellerRating, UserProfile
import logging

logger = logging.getLogger(__name__)

def get_seller_by_email(email):
    """
    Get a seller UserProfile by email. Returns None if not found or not a seller.
    """
    try:
        # Find user by email
        user = User.objects.filter(email=email).first()
        if not user:
            return None
        
        # Check if user has a profile and is a seller
        if hasattr(user, 'profile') and user.profile.is_seller:
            return user.profile
        return None
    except Exception as e:
        logger.error(f"Error getting seller by email {email}: {str(e)}")
        return None

def submit_rating_for_seller(seller_profile_id, reviewer_email, score, review_text="", reviewer_name=""):
    """
    Submit a rating for a seller WITHOUT audit logging
    """
    
    try:
        with transaction.atomic():
            # Get seller profile
            seller_profile = UserProfile.objects.get(id=seller_profile_id, is_seller=True)
            
            # Validate reviewer email
            if not reviewer_email or '@' not in reviewer_email:
                raise ValidationError("Invalid reviewer email")
            
            # Check if reviewer email belongs to a user
            reviewer_user = User.objects.filter(email=reviewer_email).first()
            
            # Check for existing review
            existing_review = SellerRating.objects.filter(
                seller=seller_profile,
                reviewer_email=reviewer_email
            ).first()
            
            if existing_review:
                # Update existing review
                existing_review.score = score
                existing_review.review_text = review_text
                if reviewer_name:
                    existing_review.reviewer_name = reviewer_name
                if reviewer_user:
                    existing_review.reviewer_user = reviewer_user
                existing_review.save()
                return existing_review, False  # Updated existing
            else:
                # Create new review
                review = SellerRating.objects.create(
                    seller=seller_profile,
                    reviewer_email=reviewer_email,
                    reviewer_name=reviewer_name or reviewer_email.split('@')[0],
                    reviewer_user=reviewer_user,
                    score=score,
                    review_text=review_text,
                    original_reviewer_id=reviewer_user.id if reviewer_user else None
                )
                return review, True  # Created new
            
    except UserProfile.DoesNotExist:
        raise ValueError(f"Seller profile with ID {seller_profile_id} not found or not a seller")
    except Exception as e:
        logger.error(f"Error submitting rating: {str(e)}")
        raise

def handle_user_deletion(user_id):
    """
    Simple user deletion handler - NO audit logging
    """
    from .models import SellerRating
    
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return False
        
        # Handle if user was a seller
        if hasattr(user, 'profile') and user.profile.is_seller:
            SellerRating.objects.filter(seller=user.profile).update(
                seller=None,
                seller_was_deleted=True,
                original_seller_email=user.email
            )
        
        # Handle if user was a reviewer
        SellerRating.objects.filter(reviewer_user=user).update(
            reviewer_user=None,
            reviewer_account_deleted=True,
            reviewer_name=f"Deleted User ({user.email})"
        )
        
        logger.info(f"Updated reviews for deleted user {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error handling user deletion: {str(e)}")
        return False

def get_seller_stats(seller_profile: UserProfile):
    """
    Get rating statistics for a seller
    """
    from django.db.models import Avg, Count, Q
    
    if not seller_profile.is_seller:
        return {
            'average_rating': 0,
            'total_ratings': 0,
            'verified_reviews': 0,
            'anonymous_reviews': 0
        }
    
    ratings = seller_profile.ratings_received.all()
    
    stats = ratings.aggregate(
        avg_rating=Avg('score'),
        total_ratings=Count('id'),
        verified_reviews=Count('id', filter=Q(reviewer_user__isnull=False)),
        anonymous_reviews=Count('id', filter=Q(reviewer_user__isnull=True))
    )
    
    # Calculate distribution
    distribution = {}
    for i in range(1, 6):
        distribution[i] = ratings.filter(score=i).count()
    
    return {
        'average_rating': round(stats['avg_rating'] or 0, 2),
        'total_ratings': stats['total_ratings'],
        'verified_reviews': stats['verified_reviews'],
        'anonymous_reviews': stats['anonymous_reviews'],
        'distribution': distribution
    }