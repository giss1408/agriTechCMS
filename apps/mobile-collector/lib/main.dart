import 'package:flutter/material.dart';

import 'data/app_state.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final state = await AppState.create();
  runApp(CabosseApp(state: state));
}

const cocoaGreen = Color(0xFF1F5A3A);
const podBrown = Color(0xFF8A4B2A);

class CabosseApp extends StatelessWidget {
  const CabosseApp({super.key, required this.state});
  final AppState state;

  @override
  Widget build(BuildContext context) {
    // Field use: large text and touch targets, high contrast, readable in direct sunlight.
    final scheme = ColorScheme.fromSeed(seedColor: cocoaGreen, secondary: podBrown);
    return MaterialApp(
      title: 'Cabosse Collecte',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: scheme,
        useMaterial3: true,
        visualDensity: VisualDensity.standard,
        textTheme: Typography.blackMountainView.apply(fontSizeFactor: 1.08),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(56), textStyle: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(52), textStyle: const TextStyle(fontSize: 16)),
        ),
        inputDecorationTheme: const InputDecorationTheme(border: OutlineInputBorder(), filled: true),
      ),
      home: ListenableBuilder(
        listenable: state,
        builder: (context, _) => state.loggedIn ? HomeScreen(state: state) : LoginScreen(state: state),
      ),
    );
  }
}
