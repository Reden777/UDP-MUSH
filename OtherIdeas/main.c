#include <stdio.h>
#include <string.h>

typedef struct {
	char name[50];
	int health;
	int mana;
	int x, y;
} Player;

void show_status(const Player *p) {
	printf("Name: %s\n", p->name);
	printf("Health: %d\n", p->health);
	printf("Mana: %d\n", p->mana);
	printf("Pos: (%d, %d)\n", p->x, p->y);
}

int main() {
	Player hero;
	printf("Welcome to the Extended Realm v0.2\n");
	printf("Enter your character name: ");

	scanf("%s", hero.name);

	hero.health = 100;
	hero.mana = 50;
	hero.x = 0;
	hero.y = 0;

	char command[20];

	while (1) {
		show_status(&hero);
		printf("\nWhat do you want to do? (n/s/q): ");
		scanf("%s", command);

		if (strcmp(command, "n") == 0) {
				hero.y++;
			}
				else if (strcmp(command, "s") == 0) {
					hero.y--;
					}
				else if (strcmp(command, "q") == 0) {
				printf("Goodbye!\n");
				break;
				}
				else {
				printf("Unknown command: %s\n", command);
				}
			}

	return 0;
}
