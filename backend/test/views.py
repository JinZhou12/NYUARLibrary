import json
from django.shortcuts import render
from django.db.utils import IntegrityError
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.decorators import api_view
from . import models
from .utils.fcns import *
import datetime
import random

# Create your views here.

UNAVAILABLE = None
MAX_RESERVATION_ID = 100000000
TOTAL_BUFFER_DAYS = 5

@api_view(['POST'])
def create_library(request):
    """
    Requires libraryName, location, phone in request body
    """
    body_unicode = request.body.decode('utf-8')
    body = json.loads(body_unicode)
    content = body['content']
    print(f'{content=}')
    models.Library.objects.create(
        libraryName=content["libraryName"],
        location=content["location"],
        phone=content["phone"]
    )

    return Response()

@api_view(['POST'])
def create_room(request):
    """
    Requires roomId, libraryName, room_type, minCapacity, maxCapacity
    noiseLevel, openHour, openMinute, closeHour, closeMinute
    in request body 
    """
    body_unicode = request.body.decode('utf-8')
    body = json.loads(body_unicode)
    content = body['content']
    print(f'{content=}')
    try:
        library = models.Library.objects.get(pk=content['libraryName'])
        openTime = datetime.time(content["openHour"], content["openMinute"])
        closeTime = datetime.time(content["closeHour"], content["closeMinute"])
        models.Room.objects.create(
            roomId=content['roomId'],
            libraryName=library,
            room_type=content["room_type"],
            minCapacity=content["minCapacity"],
            maxCapacity=content["maxCapacity"],
            noiseLevel=content["noiseLevel"],
            openTime=openTime,
            closeTime=closeTime,
        )
    except models.Library.DoesNotExist as ex:
        raise ex

    return Response()

@api_view(['POST'])
def create_student(request):
    """
    Requires studentId, email, phone in request body
    """
    body_unicode = request.body.decode('utf-8')
    body = json.loads(body_unicode)
    content = body['content']
    print(f'{content=}')
    models.Student.objects.create(
        studentId=content["studentId"],
        email=content["email"],
        phone=content["phone"]
    )

    return Response()

@api_view(['POST'])
def create_reservation(request):
    # TODO: rewrite this completely
    """
    Requires roomId, libraryName, room_type, minCapacity, maxCapacity
    noiseLevel, date, startHour, endHour, startMinute, endMinute
    in request body 
    """
    body_unicode = request.body.decode('utf-8')
    body = json.loads(body_unicode)
    content = body['content']
    print(f'{content=}')

    try:
        student = models.Student.objects.get(pk=content['studentId'])
        print(f'{student}')
        room = models.Room.objects.get(roomId=content['roomId'])
        print(f'{room=}')
        library = models.Library.objects.get(libraryName=content['libraryName'])
        print(f'{library=}')
    except models.Student.DoesNotExist as ex:
        raise ex
    except models.Room.DoesNotExist as ex:
        raise ex
    except models.Library.DoesNotExist as ex:
        raise ex
    
    year, month, day = [int(x) for x in content['date'].split('-')]
    date_dt = datetime.date(year, month, day)
    startTime = datetime.time(content["startHour"], content["startMinute"])
    endTime = datetime.time(content["endHour"], content["endMinute"])
    if date_dt < datetime.date.today() or \
        date_dt == datetime.date.today and startTime < datetime.datetime.now().time():
        raise ValueError("Requested date is already past")
    
    reservations = list(models.Reservations.objects.filter(
        studentId=None,
        roomId=content['roomId'],
        libraryName=library,
        date=date_dt,
        startTime__lte=startTime,
        endTime__gte=endTime))

    print('skibidi gyatt '+str(reservations))
    
    if len(reservations) != 1:
        raise ValueError("Section is already reserved/is not open at this time")

    leftStart = reservations[0].startTime
    rightEnd = reservations[0].endTime
    reservations[0].startTime = startTime
    reservations[0].endTime = endTime
    reservations[0].studentId = student
    print(reservations[0])
    reservations[0].save()

    if leftStart < startTime:
        models.Reservations.objects.create(
            libraryName=library,
            roomId=content["roomId"],
            date=date_dt,
            startTime=leftStart,
            endTime=startTime,
            studentId=None
        )
    
    if rightEnd > endTime:
        models.Reservations.objects.create(
            libraryName=library,
            roomId=content["roomId"],
            date=date_dt,
            startTime=endTime,
            endTime=rightEnd,
            studentId=None
        )

    return Response()

@api_view(['DELETE'])
def delete_reservation(request):
    # TODO: rewrite this completely
    """
    Requires date, startHour, endHour, startMinute, endMinute, and studentId
    in request body 
    """
    body_unicode = request.body.decode('utf-8')
    body = json.loads(body_unicode)
    content = body['content']
    print(f'{content=}')

    try:
        student = models.Student.objects.get(pk=content['studentId'])
        print(f'{student}')
    except models.Student.DoesNotExist as ex:
        raise ex
    
    year, month, day = [int(x) for x in content['date'].split('-')]
    date_dt = datetime.date(year, month, day)
    startTime = datetime.time(content["startHour"], content["startMinute"])
    endTime = datetime.time(content["endHour"], content["endMinute"])

    reservations = list(models.Reservations.objects.filter(
        studentId=content['studentId'],
        date=date_dt,
        startTime=startTime,
        endTime=endTime))
    
    if len(reservations) != 1:
        raise ValueError("Section does not exist")

    leftStart = reservations[0].startTime
    rightEnd = reservations[0].endTime
    roomId = reservations[0].roomId
    libraryName = reservations[0].libraryName
    print(leftStart, rightEnd, date_dt, roomId, libraryName)

    left_reservations = list(models.Reservations.objects.filter(
        studentId=None,
        date=date_dt,
        endTime=leftStart,
        roomId=roomId,
        libraryName=libraryName,
    ))
    right_reservations = list(models.Reservations.objects.filter(
        studentId=None,
        date=date_dt,
        startTime=rightEnd,
        roomId=roomId,
        libraryName=libraryName,
    ))
    print(left_reservations, right_reservations)

    if len(left_reservations) == 1:
        reservations[0].startTime = left_reservations[0].startTime
        left_reservations[0].delete()
    if len(right_reservations) == 1:
        reservations[0].endTime = right_reservations[0].endTime
        right_reservations[0].delete()
    
    reservations[0].studentId = None
    
    reservations[0].save()

    return Response()

@api_view(['GET'])
def checkRoomAvailability(request, roomId):
    # TODO: use helper function for retrieving results
    reservations = list(models.Reservations.objects
                        .filter(roomId=roomId, studentId=UNAVAILABLE)
                        .values('date', 'startTime', 'endTime'))
            
    resp = {'availableTimes': reservations}
    return Response(resp)

@api_view(['GET'])
def get_all_rooms(request):
    rooms = models.Room.objects.all().values()
    return Response(rooms)

@api_view(['GET'])
def get_all_reservations(request):
    res = models.Reservations.objects.all().values()
    return Response(res)

@api_view(['GET'])
def get_reservations_in_time_range(request,start_time,end_time):
    print(start_time)
    dt_start=dt_end=None
    try:
        dt_start=datetime.strptime(start_time,"%Y-%m-%dT%H:%M:%S")
        dt_end=datetime.strptime(end_time,"%Y-%m-%dT%H:%M:%S")
    except:
        raise ValueError("Invalid datetime format")
    if dt_start>=dt_end:
        raise ValueError("Start date & time must come before end date & time")
    res=models.Reservations.objects.filter(
        studentId__isnull=False,
        date__gte=dt_start,
        date__lte=dt_end,
        startTime__gte=dt_start,
        endTime__lte=dt_end,
    ).values()
    return Response(res)

@api_view(['GET'])
def get_reservations_for_student_in_time_range(request,student_id,start_time,end_time):
    print(start_time)
    dt_start=dt_end=None
    try:
        dt_start=datetime.strptime(start_time,"%Y-%m-%dT%H:%M:%S")
        dt_end=datetime.strptime(end_time,"%Y-%m-%dT%H:%M:%S")
    except:
        raise ValueError("Invalid datetime format")
    if dt_start>=dt_end:
        raise ValueError("Start date & time must come before end date & time")
    res=models.Reservations.objects.filter(
        studentId=student_id,
        date__gte=dt_start,
        date__lte=dt_end,
        startTime__gte=dt_start,
        endTime__lte=dt_end,
    ).values()
    return Response(res)

# get all reservations of a specific student 
# sample url: http://localhost:8000/reservations/?studentId=123456
@api_view(['GET'])
def get_all_reservations_for_a_student(request):
    """
    Requires studentId as query string
    """
    studentId = request.GET.get('studentId')
    reservations = models.Reservations.objects.filter(studentId=studentId)
    return Response(reservations)

@api_view(['DELETE'])
def clearAllTimeSlots(request):
    models.Reservations.objects.all().delete()
    return Response()

@api_view(['GET'])
def get_available_rooms(request):
    """
    returns a QuerySet of rooms that are not booked within
    a specified start and end time

    Requires date, startHour, startMinute, endHour, endMinute
        !date must be formatted as year-month-day
    """
    body_unicode = request.body.decode('utf-8')
    body = json.loads(body_unicode)
    content = body['content']
    print(f'{content=}')

    startTime = datetime.time(content["startHour"], content["startMinute"])
    endTime = datetime.time(content["endHour"], content["endMinute"])

    year, month, day = [int(x) for x in content['date'].split('-')]
    rsrvDate = datetime.date(year, month, day)

    """
    conditions checked to determine if a room is unavailable:
      the reservation starts within [startTime, endTime]
      the reservation ends within [startTime, endTime]
      the reservations starts before startTime and ends after endTime
    """
    unavailable = models.Reservations.objects.filter(
        Q(  Q(startTime__gte = startTime, startTime__lte = endTime) 
            | Q(endTime__gte = startTime, endTime__lte = endTime)
            | Q(startTime__lte = startTime, endTime__gte = endTime)
        ),
        date=rsrvDate
    ).values_list('roomId', flat=True)


    available = models.Room.objects.all().exclude(roomId__in=unavailable)

    return Response(available)
