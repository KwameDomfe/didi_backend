"""
Seed the database with initial cuisines, users, restaurants, categories and menu items.

Usage:
    python manage.py seed_data           # seed (skips existing records)
    python manage.py seed_data --reset   # delete seed records then re-seed
"""

import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from apps.restaurants.models import Cuisine, Restaurant, MenuCategory, MenuItem

User = get_user_model()

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

CUISINES = [
    {"name": "Nigerian",      "description": "West African cuisine from Nigeria"},
    {"name": "Ghanaian",      "description": "West African home-style cooking from Ghana"},
    {"name": "Ethiopian",     "description": "East African cuisine rich in spices and injera"},
    {"name": "Italian",       "description": "Classic pasta, pizza and Italian desserts"},
    {"name": "Chinese",       "description": "Cantonese, Szechuan and modern Chinese dishes"},
    {"name": "Indian",        "description": "Aromatic spiced curries and breads"},
    {"name": "Mexican",       "description": "Tacos, burritos and bold flavours"},
    {"name": "American",      "description": "Burgers, BBQ and comfort food"},
    {"name": "Japanese",      "description": "Sushi, ramen and Japanese classics"},
    {"name": "Mediterranean", "description": "Fresh and healthy Mediterranean dishes"},
    {"name": "Lebanese",      "description": "Shawarma, falafel and mezze platters"},
    {"name": "Thai",          "description": "Sweet, sour and spicy Thai cooking"},
]

# (username, email, password, first_name, last_name, user_type, is_staff, is_superuser)
USERS = [
    ("admin",        "admin@didi.app",    "Admin1234!",    "Admin",   "User",    "platform_admin", True,  True),
    ("vendor_kwame", "kwame@didi.app",    "Vendor1234!",   "Kwame",   "Domfe",   "vendor",         False, False),
    ("vendor_ama",   "ama@didi.app",      "Vendor1234!",   "Ama",     "Owusu",   "vendor",         False, False),
    ("customer_joe", "joe@didi.app",      "Customer123!",  "Joe",     "Mensah",  "customer",       False, False),
    ("customer_esi", "esi@didi.app",      "Customer123!",  "Esi",     "Boateng", "customer",       False, False),
    ("rider_kofi",   "kofi@didi.app",     "Rider1234!",    "Kofi",    "Asante",  "delivery",       False, False),
]

# (name, owner_username, cuisine_name, address, phone, email, price_range,
#  delivery_fee, min_order, description, features, opening_hours)
RESTAURANTS = [
    (
        "Kwame's Kitchen",
        "vendor_kwame", "Ghanaian",
        "14 Ring Road East, Accra",
        "+233201234567", "kwameskitchen@didi.app", "$$",
        5.00, 20.00,
        "Authentic Ghanaian home-style cooking. Jollof, fufu, kelewele and more.",
        ["delivery", "takeaway", "dine_in"],
        {"Monday": "8am-9pm", "Tuesday": "8am-9pm", "Wednesday": "8am-9pm",
         "Thursday": "8am-9pm", "Friday": "8am-10pm", "Saturday": "9am-10pm", "Sunday": "Closed"},
    ),
    (
        "Mama's Nigerian Spot",
        "vendor_kwame", "Nigerian",
        "22 Opebi Road, Lagos",
        "+234801234567", "mamasnigerian@didi.app", "$$",
        4.50, 15.00,
        "The taste of home — suya, egusi soup, pounded yam and more.",
        ["delivery", "takeaway", "dine_in"],
        {"Monday": "10am-10pm", "Tuesday": "10am-10pm", "Wednesday": "10am-10pm",
         "Thursday": "10am-10pm", "Friday": "10am-11pm", "Saturday": "10am-11pm", "Sunday": "12pm-9pm"},
    ),
    (
        "Bella Italia",
        "vendor_ama", "Italian",
        "8 Oxford Street, Accra",
        "+233302345678", "bellaitalia@didi.app", "$$$",
        6.00, 25.00,
        "Wood-fired pizzas, handmade pasta and authentic Italian desserts.",
        ["delivery", "dine_in", "reservations"],
        {"Monday": "Closed", "Tuesday": "12pm-10pm", "Wednesday": "12pm-10pm",
         "Thursday": "12pm-10pm", "Friday": "12pm-11pm", "Saturday": "11am-11pm", "Sunday": "11am-9pm"},
    ),
    (
        "Dragon Palace",
        "vendor_ama", "Chinese",
        "45 Independence Avenue, Accra",
        "+233303456789", "dragonpalace@didi.app", "$$",
        5.50, 20.00,
        "Cantonese and Szechuan specialities in a warm, cosy setting.",
        ["delivery", "takeaway", "dine_in"],
        {"Monday": "11am-10pm", "Tuesday": "11am-10pm", "Wednesday": "11am-10pm",
         "Thursday": "11am-10pm", "Friday": "11am-11pm", "Saturday": "11am-11pm", "Sunday": "12pm-9pm"},
    ),
]

# (restaurant_name, category_name, meal_period, description, display_order)
CATEGORIES = [
    ("Kwame's Kitchen",      "Rice Dishes",    "all_day",   "Jollof, fried rice and waakye",               1),
    ("Kwame's Kitchen",      "Soups & Stews",  "lunch",     "Light soup, groundnut soup and more",         2),
    ("Kwame's Kitchen",      "Street Snacks",  "all_day",   "Kelewele, chinchinga and koose",               3),
    ("Kwame's Kitchen",      "Drinks",         "all_day",   "Sobolo, fresh juices and soft drinks",        4),

    ("Mama's Nigerian Spot", "Grills",         "all_day",   "Suya, asun and peppered chicken",             1),
    ("Mama's Nigerian Spot", "Swallows",       "lunch",     "Pounded yam, eba and amala with soups",       2),
    ("Mama's Nigerian Spot", "Small Chops",    "all_day",   "Puff puff, samosa and spring rolls",          3),
    ("Mama's Nigerian Spot", "Drinks",         "all_day",   "Chapman, palm wine and soft drinks",          4),

    ("Bella Italia",         "Starters",       "all_day",   "Bruschetta, calamari and antipasto",          1),
    ("Bella Italia",         "Pizzas",         "dinner",    "Classic and specialty wood-fired pizzas",     2),
    ("Bella Italia",         "Pasta",          "dinner",    "Spaghetti, penne, fettuccine and more",       3),
    ("Bella Italia",         "Desserts",       "all_day",   "Tiramisu, panna cotta and gelato",            4),

    ("Dragon Palace",        "Dim Sum",        "breakfast", "Steamed and fried bite-sized dumplings",      1),
    ("Dragon Palace",        "Noodles & Rice", "all_day",   "Fried rice, chow mein and lo mein",           2),
    ("Dragon Palace",        "Mains",          "dinner",    "Kung pao, sweet & sour and more",             3),
    ("Dragon Palace",        "Soups",          "all_day",   "Hot & sour, wonton and egg drop",             4),
]

# (restaurant_name, category_name, name, description, price, is_veg, is_vegan, is_gf, spice, prep_time)
MENU_ITEMS = [
    # --- Kwame's Kitchen ---
    ("Kwame's Kitchen", "Rice Dishes",   "Jollof Rice",           "Smoky tomato jollof rice, party-style",            12.00, False, False, True,  1, 20),
    ("Kwame's Kitchen", "Rice Dishes",   "Waakye",                "Rice and beans cooked with sorghum leaves",        10.00, True,  True,  True,  0, 25),
    ("Kwame's Kitchen", "Rice Dishes",   "Fried Rice & Chicken",  "Vegetable fried rice with grilled chicken",        14.00, False, False, True,  1, 20),
    ("Kwame's Kitchen", "Soups & Stews", "Light Soup",            "Clear palm nut broth with goat meat",              13.00, False, False, True,  2, 30),
    ("Kwame's Kitchen", "Soups & Stews", "Groundnut Soup",        "Rich peanut-based soup with chicken",              13.00, False, False, True,  1, 30),
    ("Kwame's Kitchen", "Street Snacks", "Kelewele",              "Spiced fried plantain cubes",                       5.00, True,  True,  True,  2, 10),
    ("Kwame's Kitchen", "Street Snacks", "Koose",                 "Bean fritters served with pepper sauce",            4.00, True,  True,  True,  1, 15),
    ("Kwame's Kitchen", "Drinks",        "Sobolo",                "Chilled hibiscus ginger drink",                     3.00, True,  True,  True,  0,  5),
    ("Kwame's Kitchen", "Drinks",        "Fresh Coconut Water",   "Natural chilled coconut water",                     4.00, True,  True,  True,  0,  2),

    # --- Mama's Nigerian Spot ---
    ("Mama's Nigerian Spot", "Grills",    "Beef Suya",            "Spiced grilled beef skewers with yaji",            10.00, False, False, False, 3, 15),
    ("Mama's Nigerian Spot", "Grills",    "Peppered Gizzard",     "Fried gizzards in fiery pepper sauce",              9.00, False, False, True,  4, 20),
    ("Mama's Nigerian Spot", "Grills",    "Asun",                 "Spicy smoked goat meat",                           11.00, False, False, True,  3, 25),
    ("Mama's Nigerian Spot", "Swallows",  "Pounded Yam & Egusi",  "Smooth pounded yam with melon seed soup",          15.00, False, False, True,  1, 30),
    ("Mama's Nigerian Spot", "Swallows",  "Eba & Okra Soup",      "Cassava dumpling with okra and assorted meat",     14.00, False, False, True,  2, 25),
    ("Mama's Nigerian Spot", "Swallows",  "Amala & Ewedu",        "Yam flour swallow with ewedu jute leaf soup",      13.00, False, False, True,  1, 25),
    ("Mama's Nigerian Spot", "Small Chops","Puff Puff (x6)",      "Soft deep-fried dough balls",                       4.00, True,  True,  False, 0, 10),
    ("Mama's Nigerian Spot", "Small Chops","Samosa (x4)",         "Crispy pastry filled with spiced vegetables",       5.00, True,  False, False, 1, 15),
    ("Mama's Nigerian Spot", "Drinks",    "Chapman",              "Fruity non-alcoholic cocktail",                     4.00, True,  True,  True,  0,  5),

    # --- Bella Italia ---
    ("Bella Italia", "Starters",   "Bruschetta al Pomodoro",   "Grilled bread with tomato and fresh basil",         8.00, True,  True,  False, 0, 10),
    ("Bella Italia", "Starters",   "Calamari Fritti",          "Crispy fried squid rings with aioli",              12.00, False, False, False, 0, 12),
    ("Bella Italia", "Starters",   "Antipasto Misto",          "Italian cured meats and marinated vegetables",     14.00, False, False, False, 0,  8),
    ("Bella Italia", "Pizzas",     "Margherita",               "Tomato, mozzarella, fresh basil",                  18.00, True,  False, False, 0, 15),
    ("Bella Italia", "Pizzas",     "Pepperoni",                "Tomato, mozzarella, spicy pepperoni",              20.00, False, False, False, 2, 15),
    ("Bella Italia", "Pizzas",     "Quattro Formaggi",         "Four cheese pizza — mozzarella, gorgonzola, taleggio, parmesan", 22.00, True, False, False, 0, 18),
    ("Bella Italia", "Pasta",      "Spaghetti Carbonara",      "Spaghetti with guanciale, egg and pecorino",       17.00, False, False, False, 0, 15),
    ("Bella Italia", "Pasta",      "Penne Arrabbiata",         "Penne in spicy tomato and garlic sauce",           15.00, True,  True,  False, 3, 12),
    ("Bella Italia", "Pasta",      "Tagliatelle al Ragù",      "Egg pasta ribbons with slow-cooked beef ragù",     19.00, False, False, False, 1, 15),
    ("Bella Italia", "Desserts",   "Tiramisu",                 "Classic Italian coffee and mascarpone dessert",     9.00, True,  False, False, 0,  5),
    ("Bella Italia", "Desserts",   "Panna Cotta",              "Set cream with mixed berry coulis",                  8.00, True,  False, True,  0,  5),

    # --- Dragon Palace ---
    ("Dragon Palace", "Dim Sum",        "Har Gow (x4)",         "Delicate steamed shrimp dumplings",                 8.00, False, False, False, 0, 12),
    ("Dragon Palace", "Dim Sum",        "Char Siu Bao (x3)",    "Fluffy steamed BBQ pork buns",                      7.00, False, False, False, 0, 12),
    ("Dragon Palace", "Dim Sum",        "Vegetable Dumplings",  "Pan-fried tofu and vegetable dumplings",             7.00, True,  True,  False, 1, 12),
    ("Dragon Palace", "Dim Sum",        "Cheung Fun",           "Rice noodle rolls with shrimp or beef",              9.00, False, False, True,  0, 10),
    ("Dragon Palace", "Noodles & Rice", "Yang Chow Fried Rice", "Egg fried rice with shrimp and char siu pork",     13.00, False, False, True,  1, 10),
    ("Dragon Palace", "Noodles & Rice", "Beef Chow Mein",       "Stir-fried egg noodles with beef and vegetables",  14.00, False, False, False, 2, 12),
    ("Dragon Palace", "Noodles & Rice", "Vegetable Lo Mein",    "Soft noodles tossed with mixed vegetables",        12.00, True,  True,  False, 1, 10),
    ("Dragon Palace", "Mains",          "Kung Pao Chicken",     "Spicy diced chicken with peanuts and dried chilli",16.00, False, False, True,  4, 15),
    ("Dragon Palace", "Mains",          "Sweet & Sour Pork",    "Crispy pork in tangy pineapple sauce",             15.00, False, False, False, 1, 15),
    ("Dragon Palace", "Mains",          "Mapo Tofu",            "Silken tofu in spicy Szechuan bean sauce",         13.00, True,  True,  True,  4, 12),
    ("Dragon Palace", "Soups",          "Hot & Sour Soup",      "Classic Szechuan hot and sour broth",               7.00, True,  True,  True,  3,  8),
    ("Dragon Palace", "Soups",          "Wonton Soup",          "Pork wontons in clear chicken broth",               8.00, False, False, False, 0,  8),
]


class Command(BaseCommand):
    help = "Seed the database with cuisines, users, restaurants, categories and menu items"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing seed records before re-seeding",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        self._seed_cuisines()
        self._seed_users()
        self._seed_restaurants()
        self._seed_categories()
        self._seed_menu_items()

        self.stdout.write(self.style.SUCCESS("\nDatabase seeded successfully.\n"))
        self.stdout.write("Login credentials:")
        for _, email, password, _, _, user_type, _, _ in USERS:
            self.stdout.write(f"  {email:32s}  {password:16s}  ({user_type})")

    # ------------------------------------------------------------------

    def _reset(self):
        self.stdout.write(self.style.WARNING("Resetting seed data..."))
        restaurant_names = [r[0] for r in RESTAURANTS]
        MenuItem.objects.filter(restaurant__name__in=restaurant_names).delete()
        MenuCategory.objects.filter(restaurant__name__in=restaurant_names).delete()
        Restaurant.objects.filter(name__in=restaurant_names).delete()
        Cuisine.objects.filter(name__in=[c["name"] for c in CUISINES]).delete()
        User.objects.filter(email__in=[u[1] for u in USERS]).delete()
        self.stdout.write("  Reset complete.\n")

    def _seed_cuisines(self):
        self.stdout.write("Seeding cuisines...")
        for c in CUISINES:
            _, created = Cuisine.objects.get_or_create(
                name=c["name"],
                defaults={"description": c["description"]},
            )
            self.stdout.write(f"  [{'created' if created else 'exists '}] {c['name']}")

    def _seed_users(self):
        self.stdout.write("\nSeeding users...")
        for username, email, password, first_name, last_name, user_type, is_staff, is_superuser in USERS:
            if User.objects.filter(email=email).exists():
                self.stdout.write(f"  [exists ] {email}")
                continue
            User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                user_type=user_type,
                is_staff=is_staff,
                is_superuser=is_superuser,
            )
            self.stdout.write(f"  [created] {email}  ({user_type})")

    def _seed_restaurants(self):
        self.stdout.write("\nSeeding restaurants...")
        for (name, owner_username, cuisine_name, address, phone, email,
             price_range, delivery_fee, min_order, description, features, opening_hours) in RESTAURANTS:

            owner = User.objects.filter(username=owner_username).first()
            cuisine = Cuisine.objects.filter(name=cuisine_name).first()

            _, created = Restaurant.objects.get_or_create(
                name=name,
                defaults=dict(
                    owner=owner,
                    cuisine=cuisine,
                    address=address,
                    phone_number=phone,
                    email=email,
                    price_range=price_range,
                    delivery_fee=delivery_fee,
                    min_order=min_order,
                    description=description,
                    features=features,
                    opening_hours=opening_hours,
                    is_active=True,
                ),
            )
            self.stdout.write(f"  [{'created' if created else 'exists '}] {name}")

    def _seed_categories(self):
        self.stdout.write("\nSeeding categories...")
        for restaurant_name, cat_name, meal_period, description, display_order in CATEGORIES:
            restaurant = Restaurant.objects.filter(name=restaurant_name).first()
            if not restaurant:
                self.stdout.write(self.style.WARNING(f"  Restaurant not found: {restaurant_name}"))
                continue
            _, created = MenuCategory.objects.get_or_create(
                name=cat_name,
                restaurant=restaurant,
                defaults=dict(
                    meal_period=meal_period,
                    description=description,
                    display_order=display_order,
                ),
            )
            self.stdout.write(f"  [{'created' if created else 'exists '}] {restaurant_name} / {cat_name}")

    def _seed_menu_items(self):
        self.stdout.write("\nSeeding menu items...")
        for (restaurant_name, cat_name, name, description,
             price, is_veg, is_vegan, is_gf, spice, prep_time) in MENU_ITEMS:

            restaurant = Restaurant.objects.filter(name=restaurant_name).first()
            if not restaurant:
                continue
            category = MenuCategory.objects.filter(name=cat_name, restaurant=restaurant).first()
            if not category:
                self.stdout.write(self.style.WARNING(f"  Category not found: {cat_name} in {restaurant_name}"))
                continue

            _, created = MenuItem.objects.get_or_create(
                name=name,
                restaurant=restaurant,
                defaults=dict(
                    category=category,
                    description=description,
                    price=price,
                    is_available=True,
                    is_vegetarian=is_veg,
                    is_vegan=is_vegan,
                    is_gluten_free=is_gf,
                    spice_level=spice,
                    prep_time=prep_time,
                    allergens=[],
                    nutritional_info={},
                ),
            )
            self.stdout.write(f"  [{'created' if created else 'exists '}] {restaurant_name} / {name}")
