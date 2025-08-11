export function Footer() {
  return (
    <footer className="border-t mt-16">
      <div className="container mx-auto px-4 py-6 text-sm text-muted-foreground flex items-center justify-between">
        <span>© {new Date().getFullYear()} AIVO</span>
        <nav className="flex items-center gap-4">
          <a className="hover:underline" href="#">
            Terms
          </a>
          <a className="hover:underline" href="#">
            Privacy
          </a>
        </nav>
      </div>
    </footer>
  );
}
