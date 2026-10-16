import { useEffect, useState } from 'react';

// Real founding-seat counter from the platform (aggregate numbers only, CORS open for
// geoready.dev). Until it answers, or if it fails, the page keeps its previous static
// line rather than showing an invented number.
const SEATS_URL = 'https://app.geoready.dev/api/public/founding-seats';

interface Seats {
  cap: number;
  taken: number;
  open: boolean;
}

export default function FoundingSeatsStatus() {
  const [seats, setSeats] = useState<Seats | null>(null);

  useEffect(() => {
    fetch(SEATS_URL)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => data && setSeats(data))
      .catch(() => {});
  }, []);

  if (!seats) return <>Founding price: open</>;
  return seats.open ? (
    <>
      Founding price: {seats.taken} of {seats.cap} seats taken
    </>
  ) : (
    <>Founding seats are full</>
  );
}
