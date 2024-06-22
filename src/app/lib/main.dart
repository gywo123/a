import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';

void main() => runApp(MyApp());

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: GPSDataSender(),
    );
  }
}

class GPSDataSender extends StatefulWidget {
  @override
  _GPSDataSenderState createState() => _GPSDataSenderState();
}

class _GPSDataSenderState extends State<GPSDataSender> {
  String? latitude;
  String? longitude;
  String? errorMessage;
  Timer? _timer;
  int _sendCount = 0;
  String? _lastSentTime;
  int _countdownSeconds = 10;

  @override
  void initState() {
    super.initState();
    _startSendingLocationTimer();
    _getCurrentLocation();
  }

  @override
  void dispose() {
    _stopSendingLocationTimer();
    super.dispose();
  }

  void _startSendingLocationTimer() {
    _timer = Timer.periodic(Duration(seconds: 1), (_) {
      _countdownSeconds--;
      if (_countdownSeconds == 0) {
        _sendGPSDataToFastAPI();
        _sendCount++;
        _updateLastSentTime();
        _countdownSeconds = 10;
      }
      setState(() {});
    });
  }

  void _stopSendingLocationTimer() {
    _timer?.cancel();
    _timer = null;
  }

  Future<void> _getCurrentLocation() async {
    try {
      Position position = await Geolocator.getCurrentPosition();
      setState(() {
        latitude = position.latitude.toStringAsFixed(6);
        longitude = position.longitude.toStringAsFixed(6);
      });
    } catch (e) {
      setState(() {
        errorMessage = 'Failed to get location: $e';
      });
    }
  }

  Future<void> _sendGPSDataToFastAPI() async {
    try {
      Position position = await Geolocator.getCurrentPosition();
      await _postGPSDataToFastAPI(position.latitude, position.longitude);
    } catch (e) {
      setState(() {
        errorMessage = 'Failed to get location: $e';
      });
    }
  }

  Future<void> _postGPSDataToFastAPI(double lat, double lon) async {
    final url = Uri.parse('http://127.0.0.1:8000/get_gps_data');
    final body = jsonEncode({'latitude': lat, 'longitude': lon});

    try {
      final response = await http.post(url, body: body, headers: {'Content-Type': 'application/json'});
      if (response.statusCode == 200) {
        print('Location data sent to FastAPI successfully');
      } else {
        print('Failed to send location data to FastAPI: ${response.statusCode}');
      }
    } catch (e) {
      print('Error sending location data to FastAPI: $e');
    }
  }

  void _updateLastSentTime() {
    setState(() {
      _lastSentTime = DateTime.now().toString();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Guardian Angels'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (errorMessage != null)
              Text(
                errorMessage!,
                style: TextStyle(color: Colors.red),
              ),
            SizedBox(height: 16.0),
            if (latitude != null && longitude != null)
              Text(
                '현재 위치:\n위도: $latitude\n경도: $longitude',
                style: TextStyle(fontSize: 30.0),
              ),
            SizedBox(height: 20.0),
            Text(
              'GPS 데이터가 서버에 ${'$_sendCount'} 번 전송되었습니다. 다음 전송은 $_countdownSeconds 초 후에 이루어집니다.',
              style: TextStyle(fontSize: 18.0),
            ),
            SizedBox(height: 16.0),
            if (_lastSentTime != null)
              Text(
                '마지막 GPS 데이터 전송 시간: $_lastSentTime',
                style: TextStyle(fontSize: 18.0),
              ),
          ],
        ),
      ),
    );
  }
}
