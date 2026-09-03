from django.contrib import admin
from .models import Product, ProductAngle, CustomizationArea, UserDesign, PresetArtwork, MockupJob


class CustomizationAreaInline(admin.StackedInline):
    model = CustomizationArea
    extra = 0


class ProductAngleInline(admin.TabularInline):
    model = ProductAngle
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'color_name', 'price', 'is_active', 'created_at')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductAngleInline]


@admin.register(ProductAngle)
class ProductAngleAdmin(admin.ModelAdmin):
    list_display = ('name', 'product', 'angle_type', 'is_default', 'sort_order')
    list_filter = ('angle_type', 'is_default')
    search_fields = ('name', 'product__name')
    inlines = [CustomizationAreaInline]


@admin.register(CustomizationArea)
class CustomizationAreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'angle', 'max_width_mm', 'max_height_mm', 'blend_mode', 'displacement_strength')
    list_filter = ('blend_mode',)


@admin.register(UserDesign)
class UserDesignAdmin(admin.ModelAdmin):
    list_display = ('title', 'width', 'height', 'file_size_bytes', 'session_key', 'created_at')
    search_fields = ('title', 'session_key')


@admin.register(PresetArtwork)
class PresetArtworkAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_active', 'created_at')
    list_filter = ('category', 'is_active')


@admin.register(MockupJob)
class MockupJobAdmin(admin.ModelAdmin):
    list_display = ('job_id', 'product_angle', 'status', 'progress', 'execution_time_seconds', 'created_at')
    list_filter = ('status', 'blend_mode')
    search_fields = ('job_id', 'product_angle__name')
    readonly_fields = ('job_id', 'created_at', 'updated_at', 'execution_time_seconds')
