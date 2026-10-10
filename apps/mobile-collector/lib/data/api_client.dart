import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// Base URL comes from `--dart-define=API_URL=...`. The default reaches a backend running on the
/// developer's machine from the Android emulator.
const apiUrl = String.fromEnvironment('API_URL', defaultValue: 'http://10.0.2.2:8000/v1');

class ApiException implements Exception {
  ApiException(this.status, this.code, this.message);
  final int status;
  final String code;
  final String message;

  bool get isNetwork => status == 0;

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient(this._prefs);
  final SharedPreferences _prefs;
  final _http = http.Client();
  static const _timeout = Duration(seconds: 25);

  String? get accessToken => _prefs.getString('access_token');
  String? get refreshToken => _prefs.getString('refresh_token');
  bool get isLoggedIn => refreshToken != null;

  Future<void> _saveTokens(Map<String, dynamic> data) async {
    await _prefs.setString('access_token', data['access_token'] as String);
    await _prefs.setString('refresh_token', data['refresh_token'] as String);
    final user = data['user'] as Map<String, dynamic>;
    await _prefs.setString('user_name', user['name'] as String);
    await _prefs.setString('cooperative_name', (user['cooperative'] as Map<String, dynamic>)['name'] as String);
  }

  Future<void> clearSession() async {
    await _prefs.remove('access_token');
    await _prefs.remove('refresh_token');
  }

  String? get userName => _prefs.getString('user_name');
  String? get cooperativeName => _prefs.getString('cooperative_name');

  /// Responses come back gzip-compressed (dart:io sends `Accept-Encoding: gzip` and inflates
  /// transparently). Large request bodies (sync batches) are gzipped too when `compress` is set.
  Future<Map<String, dynamic>> _send(String method, String path,
      {Object? body, Map<String, String>? headers, bool auth = true, bool retried = false, bool compress = false}) async {
    final uri = Uri.parse('$apiUrl$path');
    final h = {'Content-Type': 'application/json', 'Accept-Language': 'fr', ...?headers};
    if (auth && accessToken != null) h['Authorization'] = 'Bearer $accessToken';
    http.Response res;
    try {
      final req = http.Request(method, uri)..headers.addAll(h);
      if (body != null) {
        final bytes = utf8.encode(jsonEncode(body));
        if (compress && bytes.length > 1024) {
          req.headers['Content-Encoding'] = 'gzip';
          req.bodyBytes = gzip.encode(bytes);
        } else {
          req.bodyBytes = bytes;
        }
      }
      res = await http.Response.fromStream(await _http.send(req).timeout(_timeout));
    } on SocketException {
      throw ApiException(0, 'offline', 'Pas de connexion au serveur');
    } on TimeoutException {
      throw ApiException(0, 'timeout', 'Le serveur ne répond pas');
    } on http.ClientException {
      throw ApiException(0, 'offline', 'Pas de connexion au serveur');
    }

    Map<String, dynamic> json;
    try {
      json = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    } on FormatException {
      throw ApiException(res.statusCode, 'bad_response', 'Réponse illisible du serveur (${res.statusCode})');
    }
    if (res.statusCode == 401 && auth && !retried && await _refresh()) {
      return _send(method, path, body: body, headers: headers, auth: auth, retried: true, compress: compress);
    }
    if (res.statusCode >= 400 || json['success'] != true) {
      final err = (json['errors'] as List?)?.cast<Map<String, dynamic>>().firstOrNull ?? {};
      throw ApiException(res.statusCode, (err['code'] ?? 'error') as String, (err['message'] ?? 'Erreur ${res.statusCode}') as String);
    }
    return json;
  }

  Future<bool> _refresh() async {
    final token = refreshToken;
    if (token == null) return false;
    try {
      final json = await _send('POST', '/auth/refresh', body: {'refresh_token': token}, auth: false, retried: true);
      await _saveTokens(json['data'] as Map<String, dynamic>);
      return true;
    } on ApiException catch (e) {
      if (!e.isNetwork) await clearSession(); // refresh token dead: back to the login screen
      return false;
    }
  }

  // ---------------------------------------------------------------- endpoints

  Future<String?> requestOtp(String phone) async {
    final json = await _send('POST', '/auth/request-otp', body: {'phone': phone}, auth: false);
    return (json['data'] as Map<String, dynamic>)['dev_code'] as String?;
  }

  Future<void> verifyOtp(String phone, String code, String deviceId) async {
    final json = await _send('POST', '/auth/verify-otp', body: {'phone': phone, 'otp': code, 'device_id': deviceId}, auth: false);
    final data = json['data'] as Map<String, dynamic>;
    final role = (data['user'] as Map<String, dynamic>)['role'];
    await _saveTokens(data);
    if (role != 'collector' && role != 'admin' && role != 'super_admin') {
      await clearSession();
      throw ApiException(403, 'forbidden', 'Ce compte ne peut pas saisir de collectes');
    }
  }

  Future<Map<String, dynamic>> push(Map<String, dynamic> body) async =>
      (await _send('POST', '/sync/push', body: body, compress: true))['data'] as Map<String, dynamic>;

  /// Problem report; idempotent on `client_uuid`, so the offline queue can safely retry.
  Future<String> postIssue(Map<String, dynamic> body, String deviceId) async {
    final json = await _send('POST', '/issues', body: body, headers: {'X-Device-Id': deviceId});
    return (json['data'] as Map<String, dynamic>)['reference'] as String;
  }

  /// `ref` = last `ref_hash` received: the server then omits unchanged prices, zones and settings.
  Future<Map<String, dynamic>> pull(String? since, String? ref, String deviceId) async {
    final params = {if (since != null) 'since': since, if (ref != null) 'ref': ref};
    final q = params.isEmpty ? '' : '?${Uri(queryParameters: params).query}';
    return (await _send('GET', '/sync/pull$q', headers: {'X-Device-Id': deviceId}))['data'] as Map<String, dynamic>;
  }
}
