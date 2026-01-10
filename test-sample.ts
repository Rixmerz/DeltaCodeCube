/**
 * Sample TypeScript file for testing code ingestion
 */

interface User {
  id: string;
  name: string;
  email: string;
}

class UserService {
  private users: Map<string, User>;

  constructor() {
    this.users = new Map();
  }

  addUser(user: User): void {
    this.users.set(user.id, user);
  }

  getUser(id: string): User | undefined {
    return this.users.get(id);
  }

  getAllUsers(): User[] {
    return Array.from(this.users.values());
  }
}

export function validateEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

export { UserService, User };
