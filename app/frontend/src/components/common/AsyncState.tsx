type Props = {
  status: "idle" | "loading" | "success" | "empty" | "error";
  loadingMessage?: string;
  emptyMessage?: string;
  errorMessage?: string;
  onRetry?: () => void;
  children?: React.ReactNode;
};

export function AsyncState({
  status,
  loadingMessage = "Loading…",
  emptyMessage = "Nothing to show yet.",
  errorMessage = "Something went wrong.",
  onRetry,
  children,
}: Props) {
  if (status === "loading") {
    return (
      <p className="status-message" role="status" aria-live="polite">
        {loadingMessage}
      </p>
    );
  }

  if (status === "error") {
    return (
      <div className="status-message error" role="alert" aria-live="polite">
        <p>{errorMessage}</p>
        {onRetry ? (
          <button type="button" onClick={onRetry}>
            Try again
          </button>
        ) : null}
      </div>
    );
  }

  if (status === "empty") {
    return (
      <p className="status-message" role="status" aria-live="polite">
        {emptyMessage}
      </p>
    );
  }

  if (status === "idle") {
    return (
      <p className="status-message" role="status">
        Submit a request to begin.
      </p>
    );
  }

  return <>{children}</>;
}
