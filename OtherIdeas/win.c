#include <windows.h>

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
	MessageBox(NULL, "Hello from the Win32 API!", "Msys2 gcc test", MB_OK | MB_ICONINFORMATION);
	return 0;
}
