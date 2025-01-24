from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib import auth
from .serializers import UserSerializer, ProfileSerializer, ChatSerialzer, FriendRequestSerializer
from django.db import transaction
from .models import Profile, Chat, FriendRequest
import json
from django.db.models import Q

# Create your views here.
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

                token, _ = Token.objects.get_or_create(user=user)
                
                response =  Response({
                    "status":"success",
                    "message":"You Registered Successfully",
                    "token":token.key,
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




@api_view(['POST'])
def login(request):
    data = request.data
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return Response({
            "status":"error",
            "message":"username and Password are required",
        }, status=status.HTTP_400_BAD_REQUEST)

    user = auth.authenticate(username=username, password=password)

    try:

        if user:
            auth.login(request, user)

            token, created = Token.objects.get_or_create(user=user)

            response = Response({
                "status":"success",
                "message":"You Loggedin Successfully",
                "token":token.key,
            }, status=status.HTTP_200_OK)
        

            response.set_cookie(
                key='isLoggedin',            
                value=bool(True),           
                httponly=True,
                secure=True,               
                samesite='None',  
                path='/', 
                max_age=60 * 60 * 24 * 7 
            )

            return response
        
        else:
            return Response({
                "status":"error",
                "message":"invalid Credentials",
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            "status":"error",
            "message":f"An Error occured {e}",
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def is_authenticated(request):
    try:
        return Response(True)

    except Exception as e:
        return Response({
            "status":"error",
            "message":f"{e}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
def logout(request):
    try:
        auth.logout(request)
        response = Response({
            "status":"success",
            "message":"You Logged out Successfully",
            
        }, status=status.HTTP_200_OK)

        response.delete_cookie("isLoggedin", path="/",)
    
        return response

    except Exception as e:
        return Response({
            "status":"error",
            "message":f"An Error occurred trying to log you out {e}",
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    



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
    profile_picture = request.FILES.get("profile_image")
    cover_picture = request.FILES.get("cover_image")
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
                    update_email = User.objects.create_user(email=email)
                    # update_email.save()
                    return Response({
                        "status":"success",
                        "message":"Email updated successfully"
                    }, status=status.HTTP_100_CONTINUE)
                


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
            "message":"Profile came successfully",
            "profile":serializer.data,
            "username":user.username,
            "email":user.email
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
                "profile":serialize_profile.data
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
   