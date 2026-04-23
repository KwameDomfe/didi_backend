from django.contrib import admin
from django import forms
from django.utils.html import format_html, escape
from django.utils.safestring import mark_safe
import textwrap
from django.core.files.storage import default_storage
from django.conf import settings
from uuid import uuid4
import os
import re
from .models import Restaurant, MenuCategory, MenuItem, RestaurantReview, OptionGroup, OptionChoice, Cuisine, RestaurantLike, RestaurantComment


# Cuisine admin
@admin.register(Cuisine)
class CuisineAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'image')
    search_fields = ('name',)

# Restaurant admin
@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'cuisine', 'owner', 'is_active')
    search_fields = ('name',)

@admin.register(RestaurantLike)
class RestaurantLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'restaurant', 'created_at')
    search_fields = ('user__username', 'restaurant__name')

@admin.register(RestaurantComment)
class RestaurantCommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'restaurant', 'text', 'created_at')
    search_fields = ('user__username', 'restaurant__name', 'text')

# Restaurant admin
# @admin.register(Restaurant)
# class RestaurantAdmin(admin.ModelAdmin):
#     list_display = ('name', 'cuisine', 'owner', 'is_active')
#     search_fields = ('name',)





# Custom widget to support multiple file uploads in Django admin forms
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

# Move MenuCategoryInlineForm here, after imports
class MenuCategoryInlineForm(forms.ModelForm):
    name = forms.CharField(widget=forms.TextInput(attrs={'maxlength': 100, 'placeholder': 'Category name'}))

    class Meta:
        model = MenuCategory
        fields = '__all__'

class RestaurantReviewAdminForm(forms.ModelForm):
    """Custom form for RestaurantReview to handle image uploads."""
    
    # Use a FileField to allow multiple image uploads
    image_uploads = forms.FileField(
        widget=MultipleFileInput(),
        required=False,
        help_text="Upload one or more images for the review."
    )

# Module-level widget used by MenuItem forms/admin
# class IngredientsTableWidget(forms.Widget):
#     def render(self, name, value, attrs=None, renderer=None):
#                 import json
#                 items = []
#                 if isinstance(value, str):
#                         try:
#                                 value = json.loads(value)
#                         except Exception:
#                                 value = []
#                 if isinstance(value, list):
#                         for ing in value:
#                                 if isinstance(ing, dict):
#                                         items.append({
#                                                 'name': ing.get('name',''),
#                                                 'quantity': '' if ing.get('quantity') is None else str(ing.get('quantity')),
#                                                 'unit': ing.get('unit',''),
#                                                 'notes': ing.get('notes',''),
#                                         })

#                 container_id = (attrs.get('id') if attrs else f'id_{name}') + '_stack'
#                 hidden_id = (attrs.get('id') if attrs else f'id_{name}') + '_hidden'
#                 # Common unit options for convenience
#                 unit_options = [
#                     '', 'g', 'kg', 'ml', 'l', 'tsp', 'tbsp', 'cup', 'pcs'
#                 ]

#                 def unit_select_html(selected):
#                     opts = []
#                     for u in unit_options:
#                         sel = ' selected' if u == (selected or '') else ''
#                         label = (u or '—')
#                         opts.append(f"<option value='{u}'{sel}>{label}</option>")
#                     return "<select class='vTextField unit-select'>" + ''.join(opts) + "</select>"

#                 blocks_html = ''
#                 for ing in items:
#                         blocks_html += (
#                                 "<div class='ingredient-block' style='border:1px solid #ddd;padding:10px;margin-bottom:8px;border-radius:6px;'>"
#                         f"<div><label>Name</label><input type='text' class='vTextField' placeholder='Name' value='{escape(ing['name'])}' /></div>"
#                     f"<div style='margin-top:6px;display:flex;gap:8px;align-items:center;'><label>Quantity</label><input type='number' class='vNumberField' placeholder='Quantity' min='0' step='any' value='{escape(ing['quantity'])}' /><label>Unit</label>" + unit_select_html(ing['unit']) + "</div>"
#                         f"<div style='margin-top:6px;'><label>Notes</label><input type='text' class='vTextField' placeholder='Notes' value='{escape(ing['notes'])}' /></div>"
#                                 "<div style='margin-top:8px;'><button type='button' class='button delete-row'>Remove</button></div>"
#                                 "</div>"
#                         )
#                 if not blocks_html:
#                         blocks_html = (
#                                 "<div class='ingredient-block' style='border:1px solid #ddd;padding:10px;margin-bottom:8px;border-radius:6px;'>"
#                                 "<div><label>Name</label><input type='text' class='vTextField' placeholder='Name' /></div>"
#                         "<div style='margin-top:6px;display:flex;gap:8px;align-items:center;'><label>Quantity</label><input type='number' class='vNumberField' placeholder='Quantity' min='0' step='any' /><label>Unit</label><select class='vTextField unit-select'><option value=''>—</option><option value='g'>g</option><option value='kg'>kg</option><option value='ml'>ml</option><option value='l'>l</option><option value='tsp'>tsp</option><option value='tbsp'>tbsp</option><option value='cup'>cup</option><option value='pcs'>pcs</option></select></div>"
#                                 "<div style='margin-top:6px;'><label>Notes</label><input type='text' class='vTextField' placeholder='Notes' /></div>"
#                                 "<div style='margin-top:8px;'><button type='button' class='button delete-row'>Remove</button></div>"
#                                 "</div>"
#                         )

#                 html = """
# <div class='ingredients-stack-widget' id='widget_{container_id}'>
#     <div id='{container_id}' class='ingredients-container'>
#         {blocks_html}
#     </div>
#     <div style='margin-top:6px;display:flex;gap:8px;'>
#         <button type='button' class='button add-row' data-widget='widget_{container_id}'>Add Ingredient</button>
#         <button type='button' class='button paste-helper' data-widget='widget_{container_id}'>Paste List</button>
#     </div>
#     <input type='hidden' name='{name}' id='{hidden_id}' />
# </div>
# <script>
# (function(){
#     var widgetId = 'widget_{container_id}';
#     var widget = document.getElementById(widgetId);
#     if(!widget) return;
    
#     var container = document.getElementById('{container_id}');
#     var hidden = document.getElementById('{hidden_id}');
#     if(!container || !hidden) return;
    
#     function serialize(){
#         var blocks = container.querySelectorAll('.ingredient-block');
#         var data = [];
#         blocks.forEach(function(block){
#             var nameEl = block.querySelector('div:nth-child(1) input');
#             var qtyEl = block.querySelector('div:nth-child(2) input[type="number"]');
#             var unitEl = block.querySelector('div:nth-child(2) .unit-select');
#             var notesEl = block.querySelector('div:nth-child(3) input');
#             var name = (nameEl && nameEl.value || '').trim();
#             var qty = (qtyEl && qtyEl.value || '').trim();
#             var unit = (unitEl && unitEl.value || '').trim();
#             var notes = (notesEl && notesEl.value || '').trim();
#             if(name){
#                 var obj = {name: name};
#                 if(qty){
#                     var num = Number(qty);
#                     obj.quantity = isNaN(num) ? qty : num;
#                 }
#                 if(unit) obj.unit = unit;
#                 if(notes) obj.notes = notes;
#                 data.push(obj);
#             }
#         });
#         hidden.value = JSON.stringify(data);
#     }
    
#     function createBlock(){
#         var div = document.createElement('div');
#         div.className = 'ingredient-block';
#         div.style.cssText = 'border:1px solid #ddd;padding:10px;margin-bottom:8px;border-radius:6px;';
#         div.innerHTML = '<div><label>Name</label><input type="text" class="vTextField" placeholder="Name" /></div>' +
#             '<div style="margin-top:6px;display:flex;gap:8px;align-items:center;"><label>Quantity</label><input type="number" class="vNumberField" placeholder="Quantity" min="0" step="any" /><label>Unit</label><select class="vTextField unit-select"><option value="">—</option><option value="g">g</option><option value="kg">kg</option><option value="ml">ml</option><option value="l">l</option><option value="tsp">tsp</option><option value="tbsp">tbsp</option><option value="cup">cup</option><option value="pcs">pcs</option></select></div>' +
#             '<div style="margin-top:6px;"><label>Notes</label><input type="text" class="vTextField" placeholder="Notes" /></div>' +
#             '<div style="margin-top:8px;"><button type="button" class="button delete-row" data-widget="' + widgetId + '">Remove</button></div>';
#         return div;
#     }
    
#     function addRow(){
#         var block = createBlock();
#         container.appendChild(block);
#         attachBlockListeners(block);
#         serialize();
#     }
    
#     function attachBlockListeners(block){
#         var inputs = block.querySelectorAll('input, select');
#         inputs.forEach(function(inp){
#             inp.addEventListener('input', serialize);
#             inp.addEventListener('change', serialize);
#         });
#     }
    
#     // Attach to existing blocks
#     container.querySelectorAll('.ingredient-block').forEach(attachBlockListeners);
    
#     // Event delegation on widget
#     widget.addEventListener('click', function(e){
#         var target = e.target;
        
#         // Check if this event belongs to this widget instance
#         if(target.dataset.widget !== widgetId && 
#            (!target.closest('[data-widget]') || target.closest('[data-widget]').dataset.widget !== widgetId)){
#             return;
#         }
        
#         // Handle delete
#         if(target.classList.contains('delete-row')){
#             e.preventDefault();
#             var block = target.closest('.ingredient-block');
#             if(block && container.contains(block)){
#                 block.remove();
#                 serialize();
#             }
#             return;
#         }
        
#         // Handle add
#         if(target.classList.contains('add-row')){
#             e.preventDefault();
#             addRow();
#             return;
#         }
        
#         // Handle paste
#         if(target.classList.contains('paste-helper')){
#             e.preventDefault();
#             var text = window.prompt('Paste ingredients (one per line). Format: name | qty unit | notes');
#             if(text){
#                 var lines = text.split(/\\r?\\n/).map(function(s){ return s.trim(); }).filter(Boolean);
#                 lines.forEach(function(line){
#                     var parts = line.split('|').map(function(s){ return s.trim(); });
#                     var name = parts[0] || '';
#                     var qty = '';
#                     var unit = '';
#                     var notes = parts[2] || '';
#                     if(parts[1]){
#                         var m = parts[1].split(/\\s+/);
#                         qty = m[0] || '';
#                         unit = m[1] || '';
#                     }
#                     var block = createBlock();
#                     var nameEl = block.querySelector('div:nth-child(1) input');
#                     var qtyEl = block.querySelector('div:nth-child(2) input[type="number"]');
#                     var unitEl = block.querySelector('div:nth-child(2) .unit-select');
#                     var notesEl = block.querySelector('div:nth-child(3) input');
#                     if(nameEl) nameEl.value = name;
#                     if(qtyEl) qtyEl.value = qty;
#                     if(unitEl && unit) unitEl.value = unit;
#                     if(notesEl) notesEl.value = notes;
#                     container.appendChild(block);
#                     attachBlockListeners(block);
#                 });
#                 serialize();
#             }
#         }
#     });
    
#     serialize();
# })();
# </script>
# """
#                 html = html.replace('{container_id}', container_id).replace('{hidden_id}', hidden_id).replace('{blocks_html}', blocks_html).replace('{name}', name)
#                 return mark_safe(html)

class MenuItemAdminForm(forms.ModelForm):
    ALLERGEN_CHOICES = [
        ('milk', 'Milk'),
        ('eggs', 'Eggs'),
        ('fish', 'Fish'),
        ('shellfish', 'Shellfish'),
        ('tree_nuts', 'Tree Nuts'),
        ('peanuts', 'Peanuts'),
        ('wheat', 'Wheat'),
        ('soybeans', 'Soybeans'),
        ('sesame', 'Sesame'),
        ('gluten', 'Gluten'),
        ('celery', 'Celery'),
        ('mustard', 'Mustard'),
        ('sulphites', 'Sulphites'),
        ('lupin', 'Lupin'),
        ('molluscs', 'Molluscs'),
    ]
    
    allergens = forms.MultipleChoiceField(
        choices=ALLERGEN_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select all allergens present in this dish"
    )
    
    class Meta:
        model = MenuItem
        fields = '__all__'
        
    # def __init__(self, *args, **kwargs):
    #     # super().__init__(*args, **kwargs)
    #     # if 'ingredients' in self.fields:
    #     #     self.fields['ingredients'].widget = IngredientsTableWidget()
    #     # Initialize allergens checkboxes from JSON list
    #     if self.instance and isinstance(self.instance.allergens, list):
    #         self.fields['allergens'].initial = self.instance.allergens
    
    def clean_allergens(self):
        # Return as list for JSONField storage
        return list(self.cleaned_data.get('allergens', []))
    

from django_json_widget.widgets import JSONEditorWidget
class RestaurantAdminForm(forms.ModelForm):
    FEATURES_CHOICES = [
        ('wifi', 'Wi‑Fi'),
        ('parking', 'Parking'),
        ('delivery', 'Delivery'),
        ('takeout', 'Takeout'),
        ('outdoor_seating', 'Outdoor seating'),
        ('reservations', 'Reservations'),
        ('family_friendly', 'Family friendly'),
        ('halal', 'Halal options'),
        ('vegan_options', 'Vegan options'),
        ('live_music', 'Live music'),
    ]
    
    # Generate time choices in 30-minute intervals
    TIME_CHOICES = [('', '---')] + [(f'{h:02d}:{m:02d}', f'{h:02d}:{m:02d}') for h in range(24) for m in (0, 30)]

    features = forms.MultipleChoiceField(
        choices=FEATURES_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select all features available at this restaurant"
    )

    # Per-day opening hours fields for end-user friendly input
    MON_closed = forms.BooleanField(required=False, label='Closed')
    MON_open = forms.ChoiceField(choices=TIME_CHOICES, required=False, label='Open')
    MON_close = forms.ChoiceField(choices=TIME_CHOICES, required=False, label='Close')
    TUE_closed = forms.BooleanField(required=False, label='Closed')
    TUE_open = forms.ChoiceField(choices=TIME_CHOICES, required=False, label='Open')
    TUE_close = forms.ChoiceField(choices=TIME_CHOICES, required=False, label='Close')
    WED_closed = forms.BooleanField(required=False, label='Closed')
    WED_open = forms.ChoiceField(choices=TIME_CHOICES, required=False, label='Open')
    WED_close = forms.ChoiceField(choices=TIME_CHOICES, required=False, label='Close')
    THU_closed = forms.BooleanField(required=False, label='Closed')
    THU_open = forms.ChoiceField(choices=TIME_CHOICES, required=False, label='Open')
    THU_close = forms.ChoiceField(choices=TIME_CHOICES, required=False, label='Close')
    FRI_closed = forms.BooleanField(required=False, label='Closed')
    FRI_open = forms.ChoiceField(choices=TIME_CHOICES, required=False, label='Open')
    FRI_close = forms.ChoiceField(choices=TIME_CHOICES, required=False, label='Close')
    SAT_closed = forms.BooleanField(required=False, label='Closed')
    SAT_open = forms.ChoiceField(choices=TIME_CHOICES, required=False, label='Open')
    SAT_close = forms.ChoiceField(choices=TIME_CHOICES, required=False, label='Close')
    SUN_closed = forms.BooleanField(required=False, label='Closed')
    SUN_open = forms.ChoiceField(choices=TIME_CHOICES, required=False, label='Open')
    SUN_close = forms.ChoiceField(choices=TIME_CHOICES, required=False, label='Close')

    class Meta:
        model = Restaurant
        fields = '__all__'
        widgets = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize features checkboxes from JSON list
        if self.instance and isinstance(self.instance.features, list):
            self.fields['features'].initial = self.instance.features
        # Initialize opening hours per-day fields from JSON
        days = ['MON','TUE','WED','THU','FRI','SAT','SUN']
        src = self.instance.opening_hours or {}
        for d in days:
            day = d.lower()
            day_data = src.get(day, {}) if isinstance(src, dict) else {}
            self.fields[f'{d}_closed'].initial = bool(day_data.get('closed'))
            self.fields[f'{d}_open'].initial = day_data.get('open') or None
            self.fields[f'{d}_close'].initial = day_data.get('close') or None

    def clean_features(self):
        # Return as list for JSONField storage
        return self.cleaned_data.get('features', [])

    def clean(self):
        cleaned = super().clean()
        # Build opening_hours JSON from per-day fields
        result = {}
        days = [
            ('mon','MON'),('tue','TUE'),('wed','WED'),('thu','THU'),('fri','FRI'),('sat','SAT'),('sun','SUN')
        ]
        for key, D in days:
            closed = cleaned.get(f'{D}_closed') or False
            open_t = cleaned.get(f'{D}_open')
            close_t = cleaned.get(f'{D}_close')
            if closed:
                result[key] = {'closed': True}
            else:
                if open_t and close_t:
                    result[key] = {
                        'closed': False,
                        'open': open_t if isinstance(open_t, str) else open_t.strftime('%H:%M'),
                        'close': close_t if isinstance(close_t, str) else close_t.strftime('%H:%M')
                    }
                else:
                    result[key] = {'closed': False}
        cleaned['opening_hours'] = result
        return cleaned

    def save(self, commit=True):
        """Override save to handle custom fields"""
        instance = super().save(commit=False)
        
        # opening_hours is set in clean() method via cleaned_data
        instance.opening_hours = self.cleaned_data.get('opening_hours', {})
        
        if commit:
            instance.save()
        return instance


class MenuCategoryInline(admin.StackedInline):
    """Improved inline editor for Menu Categories within a Restaurant"""
    model = MenuCategory
    form = MenuCategoryInlineForm
    extra = 1
    ordering = ['display_order']

    fieldsets = (
        (None, {
            'fields': ('name', 'image_preview', 'image')
        }),
        ('Details', {
            'fields': ('description', 'meal_period', 'display_order'),
        }),
    )
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj and obj.image:
            return mark_safe(f'<img src="{obj.image.url}" style="max-height:60px; max-width:120px; border:1px solid #ddd; margin:2px;" />')
        return "No image"
    image_preview.short_description = "Image Preview"


class MenuItemInline(admin.StackedInline):
    """Stacked inline editor for Menu Items within a Restaurant"""
    model = MenuItem
    form = MenuItemAdminForm
    extra = 1
    ordering = ['category', 'name']
    readonly_fields = ['slug']

    fieldsets = (
        (None, {
            'fields': ('name', 'category', 'price', 'is_available', 'image')
        }),
        # ('Ingredients', {
        #     'fields': ('ingredients_table', 'ingredients'),
        #     'description': 'Preview shows parsed ingredients. In the editor: add with the "Ingredient" template, ensure each item has a name; prefer numeric quantities with a unit.'
        # }),
        ('Dietary', {
            'classes': ('collapse',),
            'fields': ('is_vegetarian', 'is_vegan', 'is_gluten_free', 'spice_level', 'allergens')
        }),
        ('Operational', {
            'classes': ('collapse',),
            'fields': ('prep_time',)
        }),
    )

    # def ingredients_table(self, obj):
    #     if obj.ingredients:
    #         html = '<table style="font-size:0.95em;">'
    #         html += '<tr><th>Name</th><th>Quantity</th><th>Unit</th><th>Notes</th></tr>'
    #         for ing in obj.ingredients:
    #             html += f"<tr><td>{ing.get('name','')}</td><td>{ing.get('quantity','')}</td><td>{ing.get('unit','')}</td><td>{ing.get('notes','')}</td></tr>"
    #         html += '</table>'
    #         return mark_safe(html)
    #     return ""
    # ingredients_table.short_description = 'Ingredients'

    # def formfield_for_dbfield(self, db_field, request, **kwargs):
    #     if db_field.name == 'ingredients':
    #         kwargs['widget'] = IngredientsTableWidget()
    #     return super().formfield_for_dbfield(db_field, request, **kwargs)

# @admin.register(Restaurant)
# class RestaurantAdmin(admin.ModelAdmin):
#     form = RestaurantAdminForm
#     """Admin configuration for the Restaurant model"""
#     list_display = ('name', 'cuisine_type', 'rating', 'price_range', 'is_active', 'created_at')
#     list_filter = ('cuisine_type', 'price_range', 'is_active')
#     search_fields = ('name', 'description', 'cuisine_type')
#     prepopulated_fields = {'slug': ('name',)}
#     inlines = [MenuCategoryInline, MenuItemInline]
    
#     fieldsets = (
#         (None, {
#             'fields': ('name', 'slug', 'description', 'image', 'owner')
#         }),
#         ('Details', {
#             'fields': ('cuisine_type', 'price_range', 'rating', 'address', 'phone_number', 'email', 'website')
#         }),
#         ('Opening Hours - Monday', {
#             'fields': (('MON_closed', 'MON_open', 'MON_close'),),
#             'classes': ('collapse',),
#         }),
#         ('Opening Hours - Tuesday', {
#             'fields': (('TUE_closed', 'TUE_open', 'TUE_close'),),
#             'classes': ('collapse',),
#         }),
#         ('Opening Hours - Wednesday', {
#             'fields': (('WED_closed', 'WED_open', 'WED_close'),),
#             'classes': ('collapse',),
#         }),
#         ('Opening Hours - Thursday', {
#             'fields': (('THU_closed', 'THU_open', 'THU_close'),),
#             'classes': ('collapse',),
#         }),
#         ('Opening Hours - Friday', {
#             'fields': (('FRI_closed', 'FRI_open', 'FRI_close'),),
#             'classes': ('collapse',),
#         }),
#         ('Opening Hours - Saturday', {
#             'fields': (('SAT_closed', 'SAT_open', 'SAT_close'),),
#             'classes': ('collapse',),
#         }),
#         ('Opening Hours - Sunday', {
#             'fields': (('SUN_closed', 'SUN_open', 'SUN_close'),),
#             'classes': ('collapse',),
#         }),
#         ('Operations', {
#             'fields': ('features', 'delivery_fee', 'delivery_time', 'min_order', 'is_active')
#         }),
#     )

@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    """Admin configuration for MenuCategory"""
    list_display = ('name', 'restaurant', 'meal_period', 'display_order')
    list_filter = ('restaurant', 'meal_period')
    search_fields = ('name', 'restaurant__name')
    ordering = ('restaurant', 'display_order')


class OptionGroupInline(admin.StackedInline):
    """Inline editor for option groups inside the MenuItem admin page."""
    model = OptionGroup
    extra = 0
    show_change_link = True
    fields = ['name', 'required', 'min_selections', 'max_selections']
    verbose_name = 'Option Group'
    verbose_name_plural = 'Option Groups (customisable choices)'

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """Admin configuration for MenuItem"""
    form = MenuItemAdminForm
    inlines = [OptionGroupInline]
    list_display = ('name', 'restaurant', 'category', 'price', 'is_available', 'spice_level', 
                    # 'ingredients_table'
                    )
    list_filter = ('restaurant', 'category', 'is_available', 'is_vegetarian', 'is_vegan', 'is_gluten_free')
    search_fields = ('name', 'description', 'restaurant__name')
    ordering = ('restaurant', 'category', 'name')
    # readonly_fields = ['ingredients_table']
    fieldsets = (
        (None, {
            'fields': ('restaurant', 'category', 'name', 'description', 'price', 'image', 'is_available', 
                # 'ingredients_table', 
                # 'ingredients', 
                'allergens', 'nutritional_info', 'prep_time', 'spice_level')
        }),
    )

    # def ingredients_table(self, obj):
    #     import json
    #     ingredients = obj.ingredients
    #     if ingredients is None:
    #         ingredients = []
    #     if isinstance(ingredients, str):
    #         try:
    #             ingredients = json.loads(ingredients)
    #         except Exception:
    #             return ingredients  # fallback: show raw string
    #     if isinstance(ingredients, list):
    #         html = '<table style="font-size:0.95em;">'
    #         html += '<tr><th>Name</th><th>Quantity</th><th>Unit</th><th>Notes</th></tr>'
    #         for ing in ingredients:
    #             if isinstance(ing, dict):
    #                 html += f"<tr><td>{ing.get('name','')}</td><td>{ing.get('quantity','')}</td><td>{ing.get('unit','')}</td><td>{ing.get('notes','')}</td></tr>"
    #             else:
    #                 html += f"<tr><td colspan='4'>{str(ing)}</td></tr>"
    #         html += '</table>'
    #         return mark_safe(html)
    #     return ""
    # ingredients_table.short_description = 'Ingredients'
    # readonly_fields = ('slug',)
    
    fieldsets = (
        (None, {
            'fields': ('restaurant', 'category', 'name', 'slug', 'description', 'price', 'image')
        }),
        ('Dietary Information', {
            'classes': ('collapse',),
            'fields': ('is_available', 'is_vegetarian', 'is_vegan', 'is_gluten_free', 'spice_level', 'allergens')
        }),
        ('Operational', {
            'classes': ('collapse',),
            'fields': ('prep_time',)
        }),
    )

    # def formfield_for_dbfield(self, db_field, request, **kwargs):
    #     if db_field.name == 'ingredients':
    #         kwargs['widget'] = IngredientsTableWidget()
    #     return super().formfield_for_dbfield(db_field, request, **kwargs)

@admin.register(RestaurantReview)
class RestaurantReviewAdmin(admin.ModelAdmin):
    """Admin configuration for RestaurantReview"""
    form = RestaurantReviewAdminForm
    list_display = ('user', 'restaurant', 'rating', 'created_at')
    list_filter = ('restaurant', 'rating')
    search_fields = ('user__username', 'restaurant__name', 'comment')
    ordering = ('-created_at',)
    
    def images_preview(self, obj):
        if not obj or not obj.pk or not obj.images:
            return "No images"
        tags = []
        for url in obj.images:
            tags.append(f'<a href="{url}" target="_blank"><img src="{url}" style="max-height:80px; max-width:120px; margin:3px; border:1px solid #ddd; padding:2px;" /></a>')
        return mark_safe(''.join(tags))

    images_preview.short_description = "Current Images"

    fieldsets = (
        (None, {
            'fields': ('restaurant', 'user', 'rating', 'comment')
        }),
        ('Images', {
            'fields': ('image_uploads', 'images_preview')
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'images_preview')

# Unregister the base model if you are using a proxy model, otherwise not needed.
# Example:
# from django.contrib.auth.models import User
# from .models import MyUser
# admin.site.unregister(User)
# admin.site.register(MyUser)


# ── Option Groups & Choices ───────────────────────────────────────────────────

class OptionChoiceInline(admin.TabularInline):
    """Inline row editor for individual choices within an OptionGroup."""
    model = OptionChoice
    extra = 2
    fields = ['name', 'price_modifier']


@admin.register(OptionGroup)
class OptionGroupAdmin(admin.ModelAdmin):
    """Manage option groups (and their choices) attached to a MenuItem."""
    list_display = ['name', 'menu_item', 'required', 'min_selections', 'max_selections']
    list_filter = ['required', 'menu_item__restaurant']
    search_fields = ['name', 'menu_item__name', 'menu_item__restaurant__name']
    raw_id_fields = ['menu_item']
    inlines = [OptionChoiceInline]
