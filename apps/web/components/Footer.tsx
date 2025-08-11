export function Footer() {
  return (
    <footer className="border-t mt-16">
      <div className="container mx-auto px-4 py-6 text-sm text-muted-foreground">
        © {new Date().getFullYear()} AIVO
      </div>
    </footer>
  );
}
