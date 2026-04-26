import { Component, Input } from '@angular/core';
import { Restaurant, ScanResult } from '../../services/restaurant';

interface PrimaryLink {
  label: string;
  url: string;
}

const AMENITY_LABELS: Record<string, string> = {
  restaurant: 'Restaurant',
  cafe: 'Café',
  fast_food: 'Fast food',
  pub: 'Pub',
  bar: 'Bar',
  biergarten: 'Biergarten',
  food_court: 'Food court',
  ice_cream: 'Ice cream',
};

@Component({
  selector: 'app-restaurant-card',
  imports: [],
  templateUrl: './restaurant-card.html',
  styleUrl: './restaurant-card.scss',
})
export class RestaurantCard {
  @Input() restaurant!: Restaurant;
  @Input() scan!: ScanResult;

  get amenityLabel(): string | null {
    const a = this.restaurant.amenity;
    if (!a) return null;
    return AMENITY_LABELS[a] ?? a.replace(/_/g, ' ');
  }

  get primaryLink(): PrimaryLink {
    const dl = this.scan?.delivery_link;
    if (dl) return { label: dl.label, url: dl.url };
    if (this.restaurant.website) {
      return { label: 'Visit website', url: this.restaurant.website };
    }
    const query = encodeURIComponent(`${this.restaurant.name} ${this.restaurant.address}`.trim());
    return {
      label: 'Find on Google Maps',
      url: `https://www.google.com/maps/search/?api=1&query=${query}`,
    };
  }
}
