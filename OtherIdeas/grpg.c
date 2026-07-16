#include <windows.h>
#include <stdio.h>

// Player structure
typedef struct {
    char name[50];
    int health;
    int mana;
    int x, y;
} Player;

// Global player state (global for simplicity in this example)
Player hero = { "Hero", 100, 50, 0, 0 };

// Control Identifiers
#define ID_BTN_NORTH   101
#define ID_BTN_SOUTH   102
#define ID_BTN_QUIT    103
#define ID_EDIT_NAME   104
#define ID_BTN_SETNAME 105

// Global handles to update elements
HWND hwndNameEdit;
HWND hwndStatusLabel;

// Helper function to update the displayed status (replaces printf)
void UpdateStatusText() {
    char buffer[256];
    snprintf(buffer, sizeof(buffer), 
             "Name: %s\nHealth: %d\nMana: %d\nPos: (%d, %d)", 
             hero.name, hero.health, hero.mana, hero.x, hero.y);
    
    SetWindowText(hwndStatusLabel, buffer);
}

// Window Procedure: handles all UI events and button clicks
LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
        case WM_CREATE: {
            // Label for Name Input
            CreateWindow("STATIC", "Character Name:", 
                         WS_CHILD | WS_VISIBLE, 
                         20, 20, 120, 20, 
                         hwnd, NULL, NULL, NULL);

            // Edit Control for Name Input (replaces scanf for the name)
            hwndNameEdit = CreateWindow("EDIT", "Hero", 
                                        WS_CHILD | WS_VISIBLE | WS_BORDER, 
                                        150, 20, 120, 20, 
                                        hwnd, (HMENU)ID_EDIT_NAME, NULL, NULL);

            // Button to apply Name change
            CreateWindow("BUTTON", "Apply Name", 
                         WS_CHILD | WS_VISIBLE, 
                         280, 18, 90, 24, 
                         hwnd, (HMENU)ID_BTN_SETNAME, NULL, NULL);

            // Static Text Control to show Status (replaces show_status())
            hwndStatusLabel = CreateWindow("STATIC", "", 
                                           WS_CHILD | WS_VISIBLE, 
                                           20, 60, 350, 80, 
                                           hwnd, NULL, NULL, NULL);
            UpdateStatusText();

            // Navigation Buttons (replaces command line 'n', 's', 'q')
            CreateWindow("BUTTON", "Go North (n)", 
                         WS_CHILD | WS_VISIBLE, 
                         20, 160, 110, 30, 
                         hwnd, (HMENU)ID_BTN_NORTH, NULL, NULL);

            CreateWindow("BUTTON", "Go South (s)", 
                         WS_CHILD | WS_VISIBLE, 
                         140, 160, 110, 30, 
                         hwnd, (HMENU)ID_BTN_SOUTH, NULL, NULL);

            CreateWindow("BUTTON", "Quit (q)", 
                         WS_CHILD | WS_VISIBLE, 
                         260, 160, 110, 30, 
                         hwnd, (HMENU)ID_BTN_QUIT, NULL, NULL);
            break;
        }

        case WM_COMMAND: {
            switch (LOWORD(wParam)) {
                case ID_BTN_SETNAME:
                    // Retrieve text from the Edit box
                    GetWindowText(hwndNameEdit, hero.name, sizeof(hero.name));
                    UpdateStatusText();
                    break;

                case ID_BTN_NORTH:
                    hero.y++;
                    UpdateStatusText();
                    break;

                case ID_BTN_SOUTH:
                    hero.y--;
                    UpdateStatusText();
                    break;

                case ID_BTN_QUIT:
                    // Signal the window to close
                    DestroyWindow(hwnd);
                    break;
            }
            break;
        }

        case WM_DESTROY:
            PostQuitMessage(0);
            break;

        default:
            return DefWindowProc(hwnd, msg, wParam, lParam);
    }
    return 0;
}

// Entry Point
int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    const char CLASS_NAME[] = "Win32RPGClass";

    // Register Window Class
    WNDCLASS wc = { 0 };
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = CLASS_NAME;
    wc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);

    if (!RegisterClass(&wc)) {
        MessageBox(NULL, "Window Registration Failed!", "Error!", MB_ICONEXCLAMATION | MB_OK);
        return 0;
    }

    // Create Main Window (Fixed size, not resizable for simple layout)
    HWND hwnd = CreateWindowEx(
        0,
        CLASS_NAME,
        "Extended Realm v0.2 (Win32)",
        WS_OVERLAPPEDWINDOW & ~WS_THICKFRAME & ~WS_MAXIMIZEBOX, 
        CW_USEDEFAULT, CW_USEDEFAULT, 410, 250,
        NULL, NULL, hInstance, NULL
    );

    if (hwnd == NULL) {
        MessageBox(NULL, "Window Creation Failed!", "Error!", MB_ICONEXCLAMATION | MB_OK);
        return 0;
    }

    ShowWindow(hwnd, nCmdShow);
    UpdateWindow(hwnd);

    // Standard Win32 Message Loop
    MSG msg;
    while (GetMessage(&msg, NULL, 0, 0) > 0) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    return msg.wParam;
}
