from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib import auth
from .serializers import UserSerializer, ProfileSerializer, ChatSerialzer, FriendRequestSerializer
from django.db import transaction
from .models import Profile, Chat, FriendRequest
import json
from django.db.models import Q
from django.contrib.auth import authenticate
from rest_framework_simplejwt.views import (TokenRefreshView)
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
import jwt
from datetime import datetime, timedelta, timezone
import requests
from handlers.utils.get_agent import get_client_ip, get_location
from handlers.utils.cookies.setCookie import set_cookie


# Create your views here.
@api_view(['POST'])
@permission_classes([])
def login(request):
    username = request.data.get("username")
    password = request.data.get("password")

    try:
        user = authenticate(username=username, password=password)
    
        if user:
            auth.login(request, user)

            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            response = Response({
                "status":"success",
                "auth":True,
                "message": "Login successful"
            }, status=status.HTTP_200_OK)

            set_cookie(response, access_token, refresh)

            return response

        else:
            return Response({
                "status":"error",
                "message": "Invalid credentials"
                }, status=status.HTTP_401_UNAUTHORIZED)
        
    except Exception as e:
        return Response({"message":"Error loggin in"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    


class customTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            request.data['refresh'] = refresh_token

            response = super().post(request, *args, **kwargs)

            tokens = response.data
            access_token = tokens['access']

            res = Response()
            res.data = {"refreshed":True, "token":access_token}

            set_cookie(response, access_token, refresh_token)

            return response


        except:
            return Response({"refreshed":False}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    


@api_view(['POST'])
@permission_classes([])
def google_login(request):

    try:

        token = request.data.get('token')
        if not token:
            return Response({'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)

        google_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
        response = requests.get(google_url)
        
        if response.status_code != 200:
            return Response({
                "status":"error",
                'message': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user_data = response.json()
        email = user_data.get('email')
        given_name = user_data.get('given_name')

        if not email:
            return Response({
                "status": "error",
                'message': 'Email not found'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                "status":"error",
                'message': 'Email does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        refresh_token = RefreshToken.for_user(user)
        access_token = str(refresh_token.access_token)

        response = Response({
            "status": "success",
            "token":access_token,
            "auth":True,
            "message": "Login successful"
        }, status=status.HTTP_200_OK)

        set_cookie(response, access_token, refresh_token)

        return response
    
    except Exception as e:
        return Response({
            "status":"error",
            "message":f"Error occured {e}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([])
def google_register(request):
    try:
        token = request.data.get('token')
        if not token:
            return Response({
                "status": "error",
                'message': 'Token is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        google_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
        response = requests.get(google_url)

        if response.status_code != 200:
            return Response({
                "status": "error",
                'message': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user_data = response.json()
        email = user_data.get('email')
        picture = user_data.get('picture')
        given_name = user_data.get('given_name')
        family_name = user_data.get('family_name')

        if not email:
            return Response({
                "status": "error",
                'message': 'Email not found in Google data'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()

        if user:
            return Response({
                "status": "error",
                'message': 'Email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=given_name).exists():
            return Response({
                "status": "error",
                "message": "username already taken"
            }, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=given_name,
            last_name=family_name,
            password=None
        )

        client_ip = get_client_ip(request)
        city, country = get_location(client_ip)
        profile = Profile.objects.create(user=user, ip_address=client_ip, city=city, country=country)
        
        if picture:
            try:
                img_response = requests.get(picture)
                if img_response.status_code == 200:
                    from django.core.files.base import ContentFile
                    img_filename = f"profile_image{user.id}ddwm.jpg"
                    
                    profile.profile_picture.save(img_filename, ContentFile(img_response.content), save=True)
            except Exception as e:
                print(f"Error downloading profile picture: {e}")
        
        user.save()

        return Response({
            "status": "success",
            'message': 'Account created successfully'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        print(f"Unexpected error in google_register: {e}")
        return Response({
            "status": "error",
            "message": "An unexpected error occurred during registration"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['POST'])
@permission_classes([])
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
    return Response({
        "status":"sucess",
        "auth":True,
        "message": "You are authenticated!"
    }, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        response = Response({
            "status": "success",
            "auth":False,
            "message": "You Logged out Successfully",
        }, status=status.HTTP_200_OK)

        response.delete_cookie("isLoggedin")
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response
    except Exception as e:
        return Response({
            "status": "error", 
            "message": f"Error logging out: {e}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_users(request):
    user = request.user

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
    profile_info, _ = user.profile

    data = json.loads(request.body)
    username = data.get("username")
    email = request.data.get("email")
    user_bio = data.get("bio")
    profile_picture = data.get("profile_image")
    cover_picture = data.get("cover_image")

    try:

        with transaction.atomic():
            updated = False 

            if profile_picture:
                if profile_info.profile_picture:
                    profile_info.profile_picture.delete()
                profile_info.profile_picture = profile_picture
                updated = True

            if cover_picture:
                if profile_info.cover_picture:
                    profile_info.cover_picture.delete()
                profile_info.cover_picture = cover_picture
                updated = True

            if user_bio:
                profile_info.bio = user_bio
                updated = True

            if updated:
                profile_info.save()

            if email:
                if User.objects.filter(email=email).exists():
                    return Response({
                        "status": "error",
                        "message": f"{email} already exists"
                    }, status=status.HTTP_400_BAD_REQUEST)

                request.user.email = email

            if username:
                if User.objects.filter(username=username).exists():
                    return Response({
                        "status": "error",
                        "message":f"{username} already exists"
                    }, status=status.HTTP_400_BAD_REQUEST)

                request.user.username = username

            return Response({
                "status": "success",
                "message": "You updated your profile"
            }, status=status.HTTP_201_CREATED) 


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
        ).order_by('-sent_at')

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
def delete_chat_message(request, message_id):
    try:

        message = Chat.objects.get(message_id=message_id)

        if message:
            message.is_deleted

            return Response({
                "status":"success",
                "message":"deleted."
            }, status=status.HTTP_200_OK)
        
        else:
            return Response({
                "status":"error",
                "message": "message not available"
            }, status=status.HTTP_404_NOT_FOUND)


    except Exception as e:
        return Response({
            "status":"error",
            "message":f"Error error occured {e}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_friends_and_messages(request):
    try:
        user = request.user
        friends = FriendRequest.objects.filter(
            Q(from_user=user, is_accepted=True) | Q(to_user=user, is_accepted=True)
        ).select_related('from_user', 'to_user')

        friend_data = []
        seen_chat_pairs = set() 

        for friend in friends:
            friend_user = friend.to_user if friend.from_user == user else friend.from_user
            chat_pair = tuple(sorted([user.id, friend_user.id]))
            
            if chat_pair not in seen_chat_pairs:
                seen_chat_pairs.add(chat_pair)

                messages = Chat.objects.filter(
                    (Q(user=user) & Q(recipient=friend_user)) |
                    (Q(user=friend_user) & Q(recipient=user))
                ).order_by('sent_at').distinct()

                friend_data.append({
                    "friend": UserSerializer(friend_user).data,
                    "messages": ChatSerialzer(messages, many=True).data
                })

        return Response({"chats": friend_data}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )   
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_friend_request(request, username):
    
    try:
        try:
            to_user =User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({
                    "status":"error",
                    "message":f"{username} does not exist."
                }, status=status.HTTP_404_NOT_FOUND)
        
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
def pending_friend_requests(request):
    try:
        user = request.user
        received = FriendRequest.objects.filter(to_user=user, is_accepted=False)
        received_serialized = FriendRequestSerializer(received, many=True).data
        for item in received_serialized:
            item["request_type"] = "received"
            item["status"] = "accept" 

        sent = FriendRequest.objects.filter(from_user=user, is_accepted=False)
        sent_serialized = FriendRequestSerializer(sent, many=True).data
        for item in sent_serialized:
            item["request_type"] = "sent"
            item["status"] = "pending" 

        all_pending = received_serialized + sent_serialized

        return Response({
            "status": "success",
            "data": all_pending
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "status": "error",
            "message": f"Error fetching pending requests: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
def accept_friend_request(request, username):
    
    try:

        try:
            from_user =User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({
                    "status":"error",
                    "message":f"{username} does not exist."
                }, status=status.HTTP_404_NOT_FOUND)

        try:
            friend_request = FriendRequest.objects.get(from_user=from_user, to_user=request.user)
            friend_request.is_accepted = True
            friend_request.save()
        except FriendRequest.DoesNotExist:
            return Response({
                "status":"error",
                "message":f"No request has been sent from {username}."
            }, status=status.HTTP_404_NOT_FOUND)
        
        
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
def reject_friend_request(request, username):
    try:

        try:
            from_user =User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({
                    "status":"error",
                    "message":f"{username} does not exist."
                }, status=status.HTTP_404_NOT_FOUND)

        try:
            friend_request = FriendRequest.objects.get(from_user=from_user, to_user=request.user)
            friend_request.is_accepted = False
            friend_request.delete()
        except FriendRequest.DoesNotExist:
            return Response({
                "status":"error",
                "message":f"No request has been sent from {username}."
            }, status=status.HTTP_404_NOT_FOUND)
        
        
        return Response({
            "status":"success",
            "message":f"You are now strangers with {friend_request.from_user.username}."
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "status":"error",
            "message":f"error removing {friend_request.from_user.username}"
        } ,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                  