from .models import ProductCategory, ServiceCategory


def categories(request):
    """
    Expose product and service categories to all templates (e.g., navbar filters).
    """
    return {
        "products_categories": ProductCategory.objects.all(),
        "services_categories": ServiceCategory.objects.all(),
    }
