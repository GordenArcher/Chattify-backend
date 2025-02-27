from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib import auth
from .serializers import UserSerializer, ProfileSerializer, ChatSerialzer, FriendRequestSerializer
from django.db import transaction
from .models import Profile, Chat, FriendRequest
from django.contrib.gis.geoip2 import GeoIP2
import json
from django.db.models import Q
from django.contrib.auth import authenticate
from rest_framework_simplejwt.views import (TokenRefreshView)
from rest_framework_simplejwt.tokens import RefreshToken


# Create your views here.
@api_view(['POST'])
def login(request):
    username = request.data.get("username")
    password = request.data.get("password")

    try:
        user = authenticate(username=username, password=password)
    
        if user:
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            response = Response({
                "status":"sucess",
                "message": "Login successful"
            }, status=status.HTTP_200_OK)

            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=True,
                samesite="None",
                max_age=60 * 10,
                expires=3600,
            )

            response.set_cookie(
                key="refresh_token",
                value=str(refresh),
                httponly=True,
                secure=True,
                samesite="None",
                max_age=60 * 60 * 24 * 7, 
                expires=60 * 60 * 24 * 7,
            )

            response.set_cookie(
                key="isLoggedIn",
                value=True,
                httponly=True,
                secure=True,
                samesite="None",
                max_age=60 * 60 * 24 * 7, 
                expires=3600,
            )

            return response
        else:
            return Response({
                "status":"error",
                "message": "Invalid credentials"
                }, status=status.HTTP_401_UNAUTHORIZED)
        
    except Exception as e:
        return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    



class customTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            request.data['refresh'] = refresh_token

            response = super().post(request, *args, **kwargs)

            tokens = response.data
            access_token = tokens['access']

            res = Response()
            res.data = {"refreshed":True}

            res.set_cookie(
                key="access_token",
                value=access_token,
                secure=True,
                httponly=True,
                samesite='None',
                path='/',
                max_age=60 * 60 * 24 * 7,
                expires=60 * 60 * 24 * 7
            )

            res.set_cookie(
                key='isLoggedin',
                value=True,           
                secure=True,               
                samesite='Lax',  
                path='/',
                max_age=60 * 60 * 24 * 7,
                expires=60 * 60 * 24 * 7
            )

            return res

        except:
            return Response({"refreshed":False}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    



def get_client_ip(request):
    """Extract the real IP address even behind a proxy."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0] 
    return request.META.get('REMOTE_ADDR')



def get_location(ip):
    """Get city and country from IP address using GeoIP2."""
    try:
        geo = GeoIP2()
        location = geo.city(ip)
        city = location.get("city", "Unknown")
        country = location.get("country_name", "Unknown")
        return city, country
    except Exception:
        return "Unknown", "Unknown"


@api_view(['POST'])
def register(request):
    data = request.data
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    password2 = data.get("password2")

    try:

        if password == password2:
            if User.objects.filter(username=username).exists():
                return Response({
                    "status":"error",
                    "message":"username already exists"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            elif User.objects.filter(email=email).exists():
                return Response({
                    "status":"error",
                    "message":"Email already exists"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.save()

                client_ip = get_client_ip(request)
                city, country = get_location(client_ip)

                Profile.objects.create(user=user, ip_address=client_ip, city=city, country=country)
                
                response =  Response({
                    "status":"success",
                    "message":"You Registered Successfully",
                }, status=status.HTTP_201_CREATED)
                

            return response    
            

        else:
            return Response({
                "status":"error",
                "message":"Password does not match"
            }, status=status.HTTP_400_BAD_REQUEST)
     

    except Exception as e:
        return Response({
            "status":"error",
            "message":f"Error Registering user {e}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def protected_view(request):
    return Response({"message": "You are authenticated!"}, status=status.HTTP_200_OK)


def logout(request):
    try:
        refresh_token = request.COOKIES.get("refresh_token")
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist() 

        response = Response({
            "status": "success",
            "message": "You Logged out Successfully",
        }, status=status.HTTP_200_OK)

        response.delete_cookie("isLoggedin")
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response
    except Exception as e:
        return Response({"status": "error", "message": f"Error logging out: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_users(request):
    user = request.user
    if not user.is_authenticated:
        return Response({
            "status": "error",
            "message": "User is not authenticated"
        }, status=status.HTTP_401_UNAUTHORIZED)

    try:
        all_users = User.objects.all().exclude(id=user.id)
        
        serializer = UserSerializer(all_users, many=True)
        return Response({
            "status":"success",
            "data":{
                "users":serializer.data,
            }
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            "status":"error",
            "message":f"Error fetching users {e}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_user_profile(request):
    user = request.user
    profile_info, _ = Profile.objects.get_or_create(user=user)
    data = json.loads(request.body)
    user_bio = data.get("bio")
    profile_picture = data.get("profile_image")
    cover_picture = data.get("cover_image")
    email = request.data.get("email")

    try:

        with transaction.atomic():
            if profile_picture:
                if profile_info.profile_picture:
                    profile_info.profile_picture.delete()

                profile_info.profile_picture = profile_picture
                profile_info.save()
                return Response({
                    "status":"success",
                    "message":"Profile Image Updated successfully"
                },status=status.HTTP_201_CREATED)

            if cover_picture:
                if profile_info.cover_picture:
                    profile_info.cover_picture.delete()

                profile_info.cover_picture = cover_picture
                profile_info.save()
                return Response({
                    "status":"success",
                    "message":"Cover Image Updated successfully"
                },status=status.HTTP_201_CREATED)

            if user_bio:
                if profile_info.bio:
                   del profile_info.bio

                profile_info.bio = user_bio
                profile_info.save()

                return Response({
                    "status":"success",
                    "message":"Bio Updated successfully"
                },status=status.HTTP_201_CREATED)  
            
            if email:
                if User.objects.filter(email=email).exists():
                    return Response({
                        "status":"error",
                        "message":"Email already exists"
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
                
                else:
                    request.user.email = email
                    request.user.save()
                    return Response({
                        "status":"success",
                        "message":"Email updated successfully"
                    }, status=status.HTTP_200_OK)
                


    except Exception as e:
        return Response({
            "status":"error",
            "message":f"Error setting profile {e}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile(request):
    user = request.user
    try:
        get_user_profile = Profile.objects.get(user=user)

        serializer = ProfileSerializer(get_user_profile)

        return Response({
            "status":"success",
            "username":user.username,
            "email":user.email,
            "profile":serializer.data,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "status":"error",
            "message":f"Error getting profile {e}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_message(request, username):
    user = request.user
    friend_user = get_object_or_404(User, username=username)
    if not user.is_authenticated:
        return Response({
            "status": "error",
            "message": "User is not authenticated"
        }, status=status.HTTP_401_UNAUTHORIZED)
            
    try:

        all_messages = Chat.objects.filter(
            (Q(user=user) & Q(recipient=friend_user)) |
            (Q(user=friend_user) & Q(recipient=user))
        )

        serializer = ChatSerialzer(all_messages, many=True)
        serialize_profile = UserSerializer(friend_user)

        return Response({
            "data":{
                "messages":serializer.data,
                "friend":serialize_profile.data
            }
        },status=status.HTTP_200_OK)
        

    except Exception as e:
        return Response({
            "status":"error",
            "message":f"Error fetching messages {e}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_friend_request(request, id):
    to_user = get_object_or_404(User, id=id)
    
    try:
        if FriendRequest.objects.filter(from_user=request.user, to_user=to_user, is_accepted=False).exists():
            return Response({
                "status":"error",
                "message":"Friend request already sent."
            }, status=status.HTTP_400_BAD_REQUEST)

        elif FriendRequest.objects.filter(from_user=request.user, to_user=to_user, is_accepted=True).exists():
            return Response({
                "status":"error",
                "message":f"You're already friends with {to_user.username}"
            }, status=status.HTTP_400_BAD_REQUEST) 

        elif request.user == to_user:
            return Response({
                "status":"error",
                "message":"You cannot send a friend request to yourself."
            }, status=status.HTTP_400_BAD_REQUEST)   
                
        else:
            FriendRequest.objects.create(from_user=request.user, to_user=to_user)
            return Response({
                "status":"success",
                "message":f"Friend request sent to {to_user.username}."
            }, status=status.HTTP_200_OK)    
        
    except Exception as e:
        return Response({
            "status":"error",
            "message":"You cannot send a friend request to yourself."
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)              



    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recieved_request(request):
    try:
        received_requests = FriendRequest.objects.filter(to_user=request.user, is_accepted=False)
        serializer = FriendRequestSerializer(received_requests, many=True)
        return Response({
            "status":"success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            "status":"error",
            "message":f"error fetching recieved request"
        } ,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def friends(request):
    try:
        accepted_requests = FriendRequest.objects.filter(is_accepted=True, to_user=request.user)
        serializer = FriendRequestSerializer(accepted_requests, many=True)
        return Response({
            "status":"success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            "status":"error",
            "message":f"error fetching recieved request {e}"
        } ,status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sent_request(request):
    try:
        sent_requests = FriendRequest.objects.filter(from_user=request.user)
        serializer = FriendRequestSerializer(sent_requests, many=True)
        return Response({
            "status":"sucess",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            "status":"error",
            "message":f"error fetching sent request {e}"
        } ,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)
    
    try:
        friend_request.is_accepted = True
        friend_request.save()
        
        FriendRequest.objects.get_or_create(from_user=request.user, to_user=friend_request.from_user,  is_accepted=True)
        return Response({
            "status":"success",
            "message":f"You are now friends with {friend_request.from_user.username}."
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "status":"error",
            "message":f"error adding {friend_request.from_user.username}"
        } ,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                  



@api_view(['POST'])
def reject_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)

    try:
        friend_request.delete()
        return Response({
            "status":"success",
            "message":f"You removed {friend_request.from_user.username}."
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            "status":"error",
            "message":f"error removing {friend_request.from_user.username}"
        } ,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
   