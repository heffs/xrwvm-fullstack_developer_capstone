
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User
from .models import CarMake, CarModel
from .populate import initiate
from .restapis import get_request, analyze_review_sentiments, post_review
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from django.contrib.auth import login, authenticate
import logging
import json
from django.views.decorators.csrf import csrf_exempt

# Get an instance of a logger
logger = logging.getLogger(__name__)


# Create a `login_request` view to handle sign in request
@csrf_exempt
def login_user(request):
    # Get username and password from request.POST dictionary
    data = json.loads(request.body)
    username = data['userName']
    password = data['password']
    # Try to check if provide credential can be authenticated
    user = authenticate(username=username, password=password)
    data = {"userName": username}
    if user is not None:
        # If user is valid, call login method to login current user
        login(request, user)
        data = {"userName": username, "status": "Authenticated"}
    return JsonResponse(data)


# Create a `logout_request` view to handle sign out request
def logout(request):
    data = {"userName": ""}
    return JsonResponse(data)


# Create a `registration` view to handle sign up request
@csrf_exempt
def registration(request):
    data = json.loads(request.body)
    username = data['userName']
    password = data['password']
    first_name = data['firstName']
    last_name = data['lastName']
    email = data['email']
    username_exist = False
    try:
        # Check if user already exists
        User.objects.get(username=username)
        username_exist = True
    except Exception as e:
        print(f"Error: {e}")
        # If not, simply log this is a new user
        logger.debug("{} is a new user".format(username))

    # If it is a new user
    if not username_exist:
        # Create user in auth_user table
        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=password,
            email=email
        )
        # Login the user and redirect to list page
        login(request, user)
        data = {"userName": username, "status": "Authenticated"}
        return JsonResponse(data)
    else:
        data = {"userName": username, "error": "Already Registered"}
        return JsonResponse(data)


def get_cars(request):
    count = CarMake.objects.filter().count()
    print(count)
    if (count == 0):
        initiate()
    car_models = CarModel.objects.select_related('car_make')
    cars = []
    for car_model in car_models:
        cars.append(
            {"CarModel": car_model.name, "CarMake": car_model.car_make.name}
        )
    return JsonResponse({"CarModels": cars})


# Update the `get_dealerships` view to render the index page with
# a list of dealerships
def get_dealerships(request, state="All"):
    endpoint = f"/fetchDealers/{state}" if state != "All" else "/fetchDealers"
    dealerships = get_request(endpoint)
    return JsonResponse({"status": 200, "dealers": dealerships or []})


# Create a `get_dealer_reviews` view to render the reviews of a dealer
def get_dealer_reviews(request, dealer_id):
    if dealer_id:
        endpoint = "/fetchReviews/dealer/" + str(dealer_id)
        reviews = get_request(endpoint)

        for review_detail in reviews:
            response = analyze_review_sentiments(review_detail['review'])
            print(response)
            print(type(response))

            if response is None:
                print("Warning: sentiment analyzer returned None.")
                review_detail["sentiment"] = "unknown"

            elif "sentiment" in response:
                review_detail["sentiment"] = response["sentiment"]

            else:
                review_detail["sentiment"] = "unknown"

        return JsonResponse({"status": 200, "reviews": reviews})
    else:
        return JsonResponse([{"status": 400, "message": "Bad Request"}])


# Create a `get_dealer_details` view to render the dealer details
def get_dealer_details(request, dealer_id):
    if (dealer_id):
        endpoint = "/fetchDealer/"+str(dealer_id)
        dealership = get_request(endpoint)
        return JsonResponse({"status": 200, "dealer": dealership})
    else:
        return JsonResponse({"status": 400, "message": "Bad Request"})


# Create a `add_review` view to submit a review
@require_http_methods(["POST"])
def add_review(request):
    if request.user.is_anonymous is False:
        print("Raw request body:", request.body)
        data = json.loads(request.body)
        print("Parsed JSON data:", data)
        try:
            response = post_review(data)
            print("API response:", response)
            return JsonResponse({"status": 200})
        except json.JSONDecodeError:
            print("JSONDecodeError: Invalid JSON in request body.")
            return JsonResponse(
                {"status": 400, "message": "Invalid JSON format"})
        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse(
                {"status": 401, "message": "Error in posting review"}
            )
    else:
        return JsonResponse({"status": 403, "message": "Unauthorized"})


@ensure_csrf_cookie
def index_view(request):
    return render(request, 'react_index.html')
    # passes through Django templates
