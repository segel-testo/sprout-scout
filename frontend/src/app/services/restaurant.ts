import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface Restaurant {
  id: string;
  name: string;
  address: string;
  website: string;
  phone: string;
  amenity?: string | null;
  osm_diet_vegan?: string | null;
  osm_type?: string;
}

export interface DeliveryLink {
  platform: string;
  url: string;
  label: string;
}

export interface ScanResult {
  restaurant_id: string;
  delivery_link?: DeliveryLink | null;
}

export type ScanEvent =
  | { type: 'start'; total: number; total_available: number; capped: boolean }
  | { type: 'restaurant'; restaurant: Restaurant; scan: ScanResult }
  | { type: 'progress'; scanned: number; total: number }
  | { type: 'error'; restaurant_id: string; reason: string }
  | { type: 'done'; scanned: number; total: number };

@Injectable({ providedIn: 'root' })
export class RestaurantService {
  private apiUrl = 'http://localhost:8000/api';

  scanStream(zipCode: string, amenity?: string): Observable<ScanEvent> {
    return new Observable<ScanEvent>((subscriber) => {
      const params = new URLSearchParams({ zip_code: zipCode, country: 'AT' });
      if (amenity) params.set('amenity', amenity);
      const url = `${this.apiUrl}/restaurants/scan?${params.toString()}`;
      const source = new EventSource(url);

      const forward = (type: ScanEvent['type']) => (ev: MessageEvent) => {
        try {
          const data = JSON.parse(ev.data);
          subscriber.next({ type, ...data } as ScanEvent);
          if (type === 'done') {
            source.close();
            subscriber.complete();
          }
        } catch (e) {
          subscriber.error(e);
        }
      };

      source.addEventListener('start', forward('start') as EventListener);
      source.addEventListener('restaurant', forward('restaurant') as EventListener);
      source.addEventListener('progress', forward('progress') as EventListener);
      source.addEventListener('error', forward('error') as EventListener);
      source.addEventListener('done', forward('done') as EventListener);

      source.onerror = () => {
        if (source.readyState === EventSource.CLOSED) {
          subscriber.complete();
        }
      };

      return () => source.close();
    });
  }
}
