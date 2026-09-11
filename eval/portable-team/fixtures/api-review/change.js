class StrategyRegistry {
  constructor() { this.strategies = new Map(); }
  register(name, strategy) { this.strategies.set(name, strategy); }
  resolve(name) { return this.strategies.get(name); }
}
class QuantityValidationStrategy {
  execute(quantity) { return Number.isInteger(quantity) && quantity <= 100; }
}
class ValidationEngine {
  constructor(registry) { this.registry = registry; }
  execute(name, value) { return this.registry.resolve(name).execute(value); }
}
const registry = new StrategyRegistry();
registry.register('quantity', new QuantityValidationStrategy());
const engine = new ValidationEngine(registry);
function validateQuantity(quantity) {
  return { status: engine.execute('quantity', quantity) ? 200 : 400 };
}
module.exports = { validateQuantity };
